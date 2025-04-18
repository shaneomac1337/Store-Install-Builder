#!/bin/bash

# Parse command line arguments
offline=false
COMPONENT_TYPE="POS"
base_url="dev.cse.cloud4retail.co"
storeId=""  # Will be determined by hostname detection or user input

# Process command line options
while [ $# -gt 0 ]; do
  case "$1" in
    --offline)
      offline=true
      shift
      ;;
    --ComponentType)
      COMPONENT_TYPE="$2"
      shift 2
      ;;
    --base_url)
      base_url="$2"
      shift 2
      ;;
    --storeId)
      storeId="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--offline] [--ComponentType <POS|WDM|FLOW-SERVICE|LPA|SH|LPA-SERVICE|STOREHUB-SERVICE>] [--base_url <url>] [--storeId <id>]"
      exit 1
      ;;
  esac
done

# Validate ComponentType
valid_types=("POS" "WDM" "FLOW-SERVICE" "LPA" "SH" "LPA-SERVICE" "STOREHUB-SERVICE")
valid=false
for type in "${valid_types[@]}"; do
  if [ "$COMPONENT_TYPE" = "$type" ]; then
    valid=true
    break
  fi
done

if [ "$valid" = false ]; then
  echo "Error: Invalid ComponentType. Must be one of: ${valid_types[*]}"
  exit 1
fi

# Map shortened component types to full names
if [ "$COMPONENT_TYPE" = "LPA" ]; then
  COMPONENT_TYPE="LPA-SERVICE"
elif [ "$COMPONENT_TYPE" = "SH" ]; then
  COMPONENT_TYPE="STOREHUB-SERVICE"
fi

# Now that COMPONENT_TYPE is correctly set, capture all console output to a log file
timestamp=$(date +"%Y%m%d_%H%M%S")
log_file="GKInstall_${COMPONENT_TYPE}_$timestamp.log"
exec > >(tee -a "$log_file") 2>&1

echo "Console output is being saved to $log_file"

# Stop on first error
set -e

# Function for error handling
handle_error() {
  local line_number=$1
  echo "Error occurred at line $line_number"
  exit 1
}
trap 'handle_error $LINENO' ERR

# Function to extract version from any package filename
get_package_version() {
  local package_file="$1"
  local component_prefix="$2"
  
  # Get filename without extension
  local filename=$(basename "$package_file" | sed 's/\.[^.]*$//')
  
  # Try different patterns to extract version
  
  # Pattern 1: prefix-1.2.3 (standard format)
  if [[ "$filename" =~ ^$component_prefix-([0-9]+(\.[0-9]+)*)$ ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  
  # Pattern 2: prefix-1.2.3-suffix (with additional info)
  if [[ "$filename" =~ ^$component_prefix-([0-9]+(\.[0-9]+)*)\- ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  
  # Pattern 3: prefix_1_2_3 (underscore format)
  if [[ "$filename" =~ ^$component_prefix[_-]([0-9]+)[_\.]([0-9]+)[_\.]([0-9]+) ]]; then
    echo "${BASH_REMATCH[1]}.${BASH_REMATCH[2]}.${BASH_REMATCH[3]}"
    return 0
  fi
  
  # Pattern 4: prefix1.2.3 (no separator)
  if [[ "$filename" =~ ^$component_prefix([0-9]+(\.[0-9]+)*)$ ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  
  # Pattern 5: just extract any sequence of numbers and dots
  if [[ "$filename" =~ ([0-9]+(\.[0-9]+)*) ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  
  # If no pattern matches, return the original filename without prefix
  local version=${filename/#$component_prefix-/}
  if [ -z "$version" ]; then
    echo "Error: Could not extract version from filename $package_file"
    return 1
  fi
  
  echo "$version"
}

# Function to get JRE version from filename
get_jre_version() {
  local jre_zip="$1"
  
  # Get filename without extension
  local filename=$(basename "$jre_zip" | sed 's/\.[^.]*$//')
  
  # Special case for Java_zulujre pattern
  if [[ "$filename" =~ Java_zulujre.*?[-_]([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    # Log detection but only return the version
    echo >&2 "Detected Java version ${BASH_REMATCH[1]} from Zulu JRE filename"
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  
  # Special case for x64/x86 in filename to avoid extracting "64" as version
  if [[ "$filename" =~ x64-([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    # Log detection but only return the version
    echo >&2 "Detected Java version ${BASH_REMATCH[1]} from x64 pattern"
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  
  if [[ "$filename" =~ x86-([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    # Log detection but only return the version
    echo >&2 "Detected Java version ${BASH_REMATCH[1]} from x86 pattern"
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  
  # Try jre prefix first, then java if that fails
  local version=$(get_package_version "$jre_zip" "jre")
  if [ -z "$version" ]; then
    version=$(get_package_version "$jre_zip" "java")
  fi
  
  # Validate version format - if it's just a number like "64", it's probably wrong
  if [[ "$version" =~ ^[0-9]+$ ]] && [[ "$filename" =~ ([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    # Extract version with format like 11.0.18
    echo >&2 "Correcting invalid version '$version' to ${BASH_REMATCH[1]}"
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  
  echo "$version"
}

# Function to get Tomcat version from filename
get_tomcat_version() {
  local tomcat_zip="$1"
  get_package_version "$tomcat_zip" "tomcat"
}

# Update these lines to use the base_url
server="$base_url"
dsg_server="$base_url"

# Basic configuration
version="v1.1.0"
base_install_dir="/usr/local/gkretail"

# Set component-specific configurations
case "$COMPONENT_TYPE" in
  'POS')
    systemType="CSE-OPOS-CLOUD"
    install_dir="$base_install_dir/pos-full"
    ;;
  'WDM')
    systemType="CSE-wdm"
    install_dir="$base_install_dir/wdm"
    ;;
  'FLOW-SERVICE')
    systemType="GKR-FLOWSERVICE-CLOUD"
    install_dir="$base_install_dir/flow-service"
    ;;
  'LPA-SERVICE')
    systemType="CSE-lps-lpa"
    install_dir="$base_install_dir/lpa-service"
    ;;
  'STOREHUB-SERVICE')
    systemType="CSE-sh-cloud"
    install_dir="$base_install_dir/storehub-service"
    ;;
  *)
    systemType="CSE-OPOS-CLOUD"
    install_dir="$base_install_dir/wdm"
    ;;
esac

# Set component-specific version if available
case "$systemType" in
  "CSE-OPOS-CLOUD")
    component_version="v1.1.0"
    ;;
  "CSE-wdm")
    component_version="v1.1.0"
    ;;
  "GKR-FLOWSERVICE-CLOUD")
    component_version="v5.25.1"
    ;;
  "CSE-lps-lpa")
    component_version="v1.1.0"
    ;;
  "CSE-sh-cloud")
    component_version="v1.1.0"
    ;;
  *)
    component_version=""
    ;;
esac

# If component version is empty, use default version
if [ -z "$component_version" ]; then
  component_version="$version"
fi

# Initialize offline variables
jre_version=""
jre_file=""
tomcat_version=""
tomcat_file=""

# Set WDM SSL settings based on base install directory
security_dir="$base_install_dir/security"
# We'll find the actual certificate file dynamically later
ssl_password="changeit"

# For StoreHub, set the Firebird server path
firebird_server_path="/opt/firebird"
# If the placeholder wasn't replaced (still contains @), use a default value
if [[ "$firebird_server_path" == *@* ]]; then
  firebird_server_path="/opt/firebird"
  echo "Using default Firebird server path: $firebird_server_path"
fi

# For StoreHub, set the Jaybird driver path
firebird_driver_path_local="@FIREBIRD_DRIVER_PATH_LOCAL@"
# If the placeholder wasn't replaced (still contains @), use a default value
if [[ "$firebird_driver_path_local" == *@* ]]; then
  firebird_driver_path_local=""
  echo "No default Jaybird driver path set - will detect during installation if available"
fi

# For StoreHub, always use a fixed path on Linux to avoid any issues
if [[ "$COMPONENT_TYPE" == "STOREHUB-SERVICE" ]]; then
  # For Linux, we'll use a fixed path to avoid any issues
  firebird_server_path="/opt/firebird"
  echo "Using fixed Firebird server path: $firebird_server_path"
fi

# Check offline mode
offline_mode=$offline

# Validate WDM-specific parameters
if [ "$COMPONENT_TYPE" = "WDM" ]; then
  if [ -z "$ssl_password" ]; then
    echo "Error: ssl_password is required for WDM installation"
    exit 1
  fi
fi

# Add component-specific package directory check
if [ "$COMPONENT_TYPE" = "LPA-SERVICE" ]; then
  package_dir="offline_package_LPA"
elif [ "$COMPONENT_TYPE" = "STOREHUB-SERVICE" ]; then
  package_dir="offline_package_SH"
else
  package_dir="offline_package_$COMPONENT_TYPE"
fi

# Update offline mode checks
if [ "$offline_mode" = true ]; then
  # Check for component-specific offline package
  if [ ! -d "$package_dir" ]; then
    echo "Error: Offline package directory not found: $package_dir"
    exit 1
  fi

  # Check for required files based on component type
  if [ "$COMPONENT_TYPE" = "WDM" ]; then
    # Find JRE and Tomcat packages from dedicated Java and Tomcat directories
    jre_files=()
    
    # Try different JRE patterns in Java directory
    for pattern in "Java/*.zip" "Java/*jre*.zip" "Java/*java*.zip"; do
      if compgen -G "$pattern" > /dev/null; then
        mapfile -t new_files < <(ls $pattern 2>/dev/null)
        jre_files+=("${new_files[@]}")
      fi
    done
    
    tomcat_files=()
    # Try different Tomcat patterns in Tomcat directory
    for pattern in "Tomcat/*.zip" "Tomcat/*tomcat*.zip"; do
      if compgen -G "$pattern" > /dev/null; then
        mapfile -t new_files < <(ls $pattern 2>/dev/null)
        tomcat_files+=("${new_files[@]}")
      fi
    done
    
    # Look for any JAR file to use as installer in the component directory
    jar_files=()
    if compgen -G "$package_dir/*.jar" > /dev/null; then
      mapfile -t jar_files < <(ls $package_dir/*.jar 2>/dev/null)
    fi
    
    installer_jar=""
    has_installer_jar=false
    
    if [ "${#jar_files[@]}" -gt 0 ]; then
      if [ "${#jar_files[@]}" -gt 1 ]; then
        echo "Warning: Multiple JAR files found in $package_dir. Using the first one: $(basename ${jar_files[0]})"
      fi
      installer_jar="${jar_files[0]}"
      has_installer_jar=true
      echo "Found installer JAR: $(basename ${jar_files[0]})"
    fi
    
    # Initialize required files with Launcher binary
    required_files=("$package_dir/Launcher.run")
    
    # Process JRE files if available
    if [ "${#jre_files[@]}" -gt 0 ]; then
      jre_file="${jre_files[0]}"
      jre_version=$(get_jre_version "$(basename ${jre_files[0]})")
      echo "Found JRE/Java package: $(basename ${jre_files[0]}), version: $jre_version"
      required_files+=("$jre_file")
    else
      echo "Error: No JRE/Java package found in Java directory"
      exit 1
    fi
    
    # Process Tomcat files if available
    if [ "${#tomcat_files[@]}" -gt 0 ]; then
      tomcat_file="${tomcat_files[0]}"
      tomcat_version=$(get_tomcat_version "$(basename ${tomcat_files[0]})")
      echo "Found Tomcat package: $(basename ${tomcat_files[0]}), version: $tomcat_version"
      required_files+=("$tomcat_file")
    else
      echo "Error: No Tomcat package found in Tomcat directory"
      exit 1
    fi
    
    # Add installer.jar to required files if it exists
    if [ "$has_installer_jar" = true ]; then
      required_files+=("$installer_jar")
    fi
  elif [ "$COMPONENT_TYPE" = "STOREHUB-SERVICE" ]; then
    # For StoreHub components - with Jaybird support
    # Find JRE and Tomcat packages from dedicated Java and Tomcat directories
    jre_files=()
    
    # Try different JRE patterns in Java directory
    for pattern in "Java/*.zip" "Java/*jre*.zip" "Java/*java*.zip"; do
      if compgen -G "$pattern" > /dev/null; then
        mapfile -t new_files < <(ls $pattern 2>/dev/null)
        jre_files+=("${new_files[@]}")
      fi
    done
    
    tomcat_files=()
    # Try different Tomcat patterns in Tomcat directory
    for pattern in "Tomcat/*.zip" "Tomcat/*tomcat*.zip"; do
      if compgen -G "$pattern" > /dev/null; then
        mapfile -t new_files < <(ls $pattern 2>/dev/null)
        tomcat_files+=("${new_files[@]}")
      fi
    done
    
    # Look for Jaybird JAR files
    jaybird_files=()
    if compgen -G "Jaybird/*.jar" > /dev/null; then
      mapfile -t jaybird_files < <(ls Jaybird/*.jar 2>/dev/null)
    fi
    
    jaybird_file=""
    has_jaybird=false
    
    if [ "${#jaybird_files[@]}" -gt 0 ]; then
      if [ "${#jaybird_files[@]}" -gt 1 ]; then
        echo "Warning: Multiple Jaybird JAR files found. Using the first one: $(basename ${jaybird_files[0]})"
      fi
      jaybird_file="${jaybird_files[0]}"
      has_jaybird=true
      echo "Found Jaybird driver: $(basename ${jaybird_files[0]})"
      
      # Update the firebird_driver_path_local to point to the actual JAR file, not just the directory
      firebird_driver_path_local="$jaybird_file"
      echo "Updated Jaybird driver path to: $firebird_driver_path_local"
    else
      echo "Warning: No Jaybird driver found in Jaybird directory"
    fi
    
    # Look for any JAR file to use as installer in the component directory
    jar_files=()
    if compgen -G "$package_dir/*.jar" > /dev/null; then
      mapfile -t jar_files < <(ls $package_dir/*.jar 2>/dev/null)
    fi
    
    installer_jar=""
    has_installer_jar=false
    
    if [ "${#jar_files[@]}" -gt 0 ]; then
      if [ "${#jar_files[@]}" -gt 1 ]; then
        echo "Warning: Multiple JAR files found in $package_dir. Using the first one: $(basename ${jar_files[0]})"
      fi
      installer_jar="${jar_files[0]}"
      has_installer_jar=true
      echo "Found installer JAR: $(basename ${jar_files[0]})"
    fi
    
    # Initialize required files with Launcher binary
    required_files=("$package_dir/Launcher.run")
    
    # Process JRE files if available
    if [ "${#jre_files[@]}" -gt 0 ]; then
      jre_file="${jre_files[0]}"
      jre_version=$(get_jre_version "$(basename ${jre_files[0]})")
      echo "Found JRE/Java package: $(basename ${jre_files[0]}), version: $jre_version"
      required_files+=("$jre_file")
    else
      echo "Error: No JRE/Java package found for $COMPONENT_TYPE"
      exit 1
    fi
    
    # Process Tomcat files if available
    if [ "${#tomcat_files[@]}" -gt 0 ]; then
      tomcat_file="${tomcat_files[0]}"
      tomcat_version=$(get_tomcat_version "$(basename ${tomcat_files[0]})")
      echo "Found Tomcat package: $(basename ${tomcat_files[0]}), version: $tomcat_version"
      required_files+=("$tomcat_file")
    else
      echo "Error: No Tomcat package found for $COMPONENT_TYPE"
      exit 1
    fi
    
    # Add Jaybird file to required files if it exists
    if [ "$has_jaybird" = true ]; then
      required_files+=("$jaybird_file")
    fi
    
    # Add installer.jar to required files if it exists
    if [ "$has_installer_jar" = true ]; then
      required_files+=("$installer_jar")
    fi
  else
    # For other components - generic approach with improved detection
    # Find JRE and Tomcat packages from dedicated Java and Tomcat directories
    jre_files=()
    
    # Try different JRE patterns in Java directory
    for pattern in "Java/*.zip" "Java/*jre*.zip" "Java/*java*.zip"; do
      if compgen -G "$pattern" > /dev/null; then
        mapfile -t new_files < <(ls $pattern 2>/dev/null)
        jre_files+=("${new_files[@]}")
      fi
    done
    
    tomcat_files=()
    # Try different Tomcat patterns in Tomcat directory
    for pattern in "Tomcat/*.zip" "Tomcat/*tomcat*.zip"; do
      if compgen -G "$pattern" > /dev/null; then
        mapfile -t new_files < <(ls $pattern 2>/dev/null)
        tomcat_files+=("${new_files[@]}")
      fi
    done
    
    # Look for any JAR file to use as installer in the component directory
    jar_files=()
    if compgen -G "$package_dir/*.jar" > /dev/null; then
      mapfile -t jar_files < <(ls $package_dir/*.jar 2>/dev/null)
    fi
    
    installer_jar=""
    has_installer_jar=false
    
    if [ "${#jar_files[@]}" -gt 0 ]; then
      if [ "${#jar_files[@]}" -gt 1 ]; then
        echo "Warning: Multiple JAR files found in $package_dir. Using the first one: $(basename ${jar_files[0]})"
      fi
      installer_jar="${jar_files[0]}"
      has_installer_jar=true
      echo "Found installer JAR: $(basename ${jar_files[0]})"
    fi
    
    # Initialize required files with Launcher binary
    required_files=("$package_dir/Launcher.run")
    
    # Process JRE files if available
    if [ "${#jre_files[@]}" -gt 0 ]; then
      jre_file="${jre_files[0]}"
      jre_version=$(get_jre_version "$(basename ${jre_files[0]})")
      echo "Found JRE/Java package: $(basename ${jre_files[0]}), version: $jre_version"
      required_files+=("$jre_file")
    else
      echo "No JRE/Java package found for $COMPONENT_TYPE."
    fi
    
    # Process Tomcat files if available
    if [ "${#tomcat_files[@]}" -gt 0 ]; then
      tomcat_file="${tomcat_files[0]}"
      tomcat_version=$(get_tomcat_version "$(basename ${tomcat_files[0]})")
      echo "Found Tomcat package: $(basename ${tomcat_files[0]}), version: $tomcat_version"
      required_files+=("$tomcat_file")
    else
      echo "No Tomcat package found for $COMPONENT_TYPE."
    fi
    
    # Add installer.jar to required files if it exists
    if [ "$has_installer_jar" = true ]; then
      required_files+=("$installer_jar")
    fi
  fi

  for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
      echo "Error: Required file not found: $file"
      exit 1
    fi
  done

  # Update file paths to use component-specific directory
  launcher_path="$package_dir/Launcher.run"
  # JRE and Tomcat files are already set in the dynamic detection code above
fi

# Create installation directory if it doesn't exist
mkdir -p "$install_dir"

# Check if this is an update of an existing installation
isUpdate=false
if [ -d "$install_dir" ]; then
    # Check for log folders
    logPath="$install_dir/log"
    logsPath="$install_dir/logs"
    
    # Determine which log folder exists
    logFolderPath=""
    if [ -d "$logPath" ]; then
        logFolderPath="$logPath"
    elif [ -d "$logsPath" ]; then
        logFolderPath="$logsPath"
    fi
    
    # If a log folder exists, check for recent activity (last 7 days)
    if [ -n "$logFolderPath" ]; then
        echo "Found existing installation at $install_dir with log folder at $logFolderPath"
        
        # Get files modified in the last 7 days
        recentFiles=$(find "$logFolderPath" -type f -mtime -7 2>/dev/null)
        recentFileCount=$(echo "$recentFiles" | grep -v '^$' | wc -l)
        
        if [ $recentFileCount -gt 0 ]; then
            echo "Found $recentFileCount recently modified log files (within 7 days)"
            echo "This appears to be an active installation. Performing update instead of full installation."
            isUpdate=true
        else
            echo "No recent activity found in logs. Performing full installation."
        fi
    else
        echo "No log folder found. Performing full installation."
    fi
else
    echo "Installation directory does not exist. Performing full installation."
fi

# If this is an update in offline mode and we have an installer jar, copy it to the temp directory
if [ "$isUpdate" = true ] && [ "$offline_mode" = true ] && [ "$has_installer_jar" = true ]; then
    installerTempDir="$install_dir/installer/temp"
    
    # Create the temp directory if it doesn't exist
    if [ ! -d "$installerTempDir" ]; then
        echo "Creating installer temp directory: $installerTempDir"
        mkdir -p "$installerTempDir"
    fi
    
    # Copy the installer jar to the temp directory
    installerJarDest="$installerTempDir/installer.jar"
    echo "Copying installer JAR for offline update: $installer_jar -> $installerJarDest"
    if cp "$installer_jar" "$installerJarDest"; then
        echo "Successfully copied installer JAR for offline update"
    else
        echo "Warning: Failed to copy installer JAR for offline update"
    fi
fi

# Get hostname
hs=$(hostname)
if [ -z "$hs" ]; then
  echo "Warning: Could not read hostname. Falling back to manual input."
else
  echo "-------------------"
  echo "Hostname  : $hs"
  echo "==================="
fi

# Initialize variables for Store Number and Workstation ID
storeNumber=""
workstationId=""

# Try to extract Store Number and Workstation ID from hostname
hostnameDetected=false

# For update mode, we must extract values from the existing installation
if [ "$isUpdate" = true ]; then
  echo "Running in update mode - attempting to extract store and workstation IDs from existing installation"
  
  # Look for station.properties in the installation directory
  station_properties_path="$install_dir/station.properties"
  if [ -f "$station_properties_path" ]; then
    echo "Found existing station.properties at: $station_properties_path"
    
    # Extract the store ID
    store_id_line=$(grep "station.storeId=" "$station_properties_path")
    if [ -n "$store_id_line" ]; then
      storeNumber=$(echo "$store_id_line" | cut -d'=' -f2)
      echo "Found Store ID in station.properties: $storeNumber"
    fi
    
    # Extract the workstation ID
    workstation_id_line=$(grep "station.workstationId=" "$station_properties_path")
    if [ -n "$workstation_id_line" ]; then
      workstationId=$(echo "$workstation_id_line" | cut -d'=' -f2)
      echo "Found Workstation ID in station.properties: $workstationId"
    fi
    
    # If both values were found, skip hostname detection
    if [ -n "$storeNumber" ] && [ -n "$workstationId" ]; then
      hostnameDetected=true
      echo "Using Store ID and Workstation ID from existing installation"
    else
      echo -e "\033[1;31mError: Could not extract complete information from station.properties\033[0m"
      echo -e "\033[1;31mUpdate not possible. Exiting.\033[0m"
      exit 1
    fi
  else
    echo -e "\033[1;31mError: No station.properties found at: $station_properties_path\033[0m"
    echo -e "\033[1;31mUpdate not possible. Exiting.\033[0m"
    exit 1
  fi
else
  # For new installations, detect from hostname or prompt user
  if [ -n "$hs" ]; then
    # Try different patterns:
    # 1. XXXX-YYY format (e.g., R005-101, 1674-101)
    # 2. SOMENAME-XXXX-YYY format (e.g., SOMENAME-1674-101)
    
    # Extract the last part (workstation ID)
    if [[ "$hs" =~ ([A-Za-z0-9]+)-POS-([0-9]+)$ ]]; then
      storeId="${BASH_REMATCH[1]}"
      workstationId="${BASH_REMATCH[2]}"
      
      # If storeId contains a dash, it might be SOMENAME-1674-101 format
      if [[ "$storeId" =~ .*-([0-9]{4})$ ]]; then
        storeNumber="${BASH_REMATCH[1]}"
      else
        # Direct format like R005-101
        storeNumber="$storeId"
      fi
      
      # Validate extracted parts
      # Accept any alphanumeric characters for store ID with at least 1 character
      if echo "$storeNumber" | grep -qE '^[A-Za-z0-9_\-\.]+$'; then
        if [[ "$workstationId" =~ ^[0-9]+$ ]]; then
          hostnameDetected=true
          echo "Successfully detected values from hostname:"
          echo "Store Number: $storeNumber"
          echo "Workstation ID: $workstationId"
        fi
      fi
    fi
  fi

  # If hostname detection failed, try file detection
  if [ "$hostnameDetected" = false ]; then
    if [ -n "$hs" ]; then
      echo "Could not extract valid Store Number and Workstation ID from hostname."
      echo "Trying file detection..."
    fi
    
    
# File detection for the current component ($COMPONENT_TYPE)
fileDetectionEnabled=true
componentType="$COMPONENT_TYPE"

# Check if we're using base directory or custom paths
useBaseDirectory="True"

if [ "$useBaseDirectory" = "True" ]; then
    # Use base directory approach
    basePath="/usr/local/gkretail/stations"
    declare -A customFilenames
    customFilenames["POS"]="POS.station"
    customFilenames["WDM"]="WDM.station"
    customFilenames["FLOW-SERVICE"]="FLOW-SERVICE.station"
    customFilenames["LPA-SERVICE"]="LPA.station"
    customFilenames["STOREHUB-SERVICE"]="SH.station"

    # Get the appropriate station file for the current component
    stationFileName="${customFilenames[$componentType]}"
    if [ -z "$stationFileName" ]; then
        stationFileName="$componentType.station"
    fi

    stationFilePath="$basePath/$stationFileName"
else
    # Use custom paths approach
    declare -A customPaths
    customPaths["POS"]=""
    customPaths["WDM"]=""
    customPaths["FLOW-SERVICE"]=""
    customPaths["LPA-SERVICE"]=""
    customPaths["STOREHUB-SERVICE"]=""
    
    # Get the appropriate station file path for the current component
    stationFilePath="${customPaths[$componentType]}"
    if [ -z "$stationFilePath" ]; then
        echo "Warning: No custom path defined for $componentType"
        # Fallback to a default path
        stationFilePath="/usr/local/gkretail/stations/$componentType.station"
    fi
fi

# Check if hostname detection failed and file detection is enabled
if [ "$hostnameDetected" = false ] && [ "$fileDetectionEnabled" = true ]; then
    echo "Trying file detection for $componentType using $stationFilePath"
    
    if [ -f "$stationFilePath" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            if [[ "$line" =~ StoreID=(.+) ]]; then
                storeNumber="${BASH_REMATCH[1]}"
                echo "Found Store ID in file: $storeNumber"
            fi
            
            if [[ "$line" =~ WorkstationID=(.+) ]]; then
                workstationId="${BASH_REMATCH[1]}"
                echo "Found Workstation ID in file: $workstationId"
            fi
        done < "$stationFilePath"
        
        # Validate extracted values
        if [ -n "$storeNumber" ] && [[ "$workstationId" =~ ^[0-9]+$ ]]; then
            # Export the variable to ensure it's available in the parent scope
            export hostnameDetected=true
            echo "Successfully detected values from file:"
            echo "Store Number: $storeNumber"
            echo "Workstation ID: $workstationId"
        fi
    else
        echo "Station file not found at: $stationFilePath"
    fi
fi

  fi

  # If both hostname and file detection failed, prompt for manual input
  if [ "$hostnameDetected" = false ]; then
    echo "Falling back to manual input."
    
    # Prompt for Store Number
    echo "Please enter the Store Number in one of these formats (or any custom format):"
    echo "  - 4 digits (e.g., 1234)"
    echo "  - 1 letter + 3 digits (e.g., R005)"
    echo "  - 2 letters + 2 digits (e.g., CA45)"
    echo "  - Custom format (e.g., STORE-105)"
    read -p "Store Number: " storeNumber

    # Validate that something was entered
    if [ -z "$storeNumber" ]; then
      echo "Store Number cannot be empty. Please try again."
      read -p "Store Number: " storeNumber
    fi
    
    # Prompt for Workstation ID
    while true; do
      read -p "Please enter the Workstation ID (numeric): " workstationId
      if [[ "$workstationId" =~ ^[0-9]+$ ]]; then
        break
      fi
      echo "Invalid input. Please enter a numeric Workstation ID."
    done
  fi
fi

# Print final results
echo "-------------------"
echo "StoreNr   : $storeNumber"
echo "WorkstationId: $workstationId"
echo "-------------------"

# After the basic configuration section, update the onboarding call
echo "Starting onboarding process for $COMPONENT_TYPE"

# Skip onboarding and store initialization if this is an update
if [ "$isUpdate" = false ]; then
    # Call the onboarding script with the appropriate component type
    if ! ./onboarding.sh --ComponentType "$COMPONENT_TYPE" --base_url "$base_url"; then
      echo "Error during $COMPONENT_TYPE onboarding"
      exit 1
    fi
    echo "$COMPONENT_TYPE onboarding completed successfully"

    # Execute store initialization right after successful onboarding
    # Skip store initialization for WDM
    if [ "$COMPONENT_TYPE" != "WDM" ]; then
      echo "Starting store initialization..."
      store_init_script="$PWD/store-initialization.sh"
      if [ -f "$store_init_script" ]; then
        # Update get_store.json with the store ID
        get_store_json_path="$PWD/helper/init/get_store.json"
        if [ -f "$get_store_json_path" ]; then
          echo "Creating processed copy of get_store.json with Store ID: $storeNumber"
          # Create a processed directory if it doesn't exist
          mkdir -p "$PWD/helper/init"
          # Create a processed copy
          processed_get_store_path="$PWD/helper/init/get_store_processed.json"
          # Copy the original to processed file
          cp "$get_store_json_path" "$processed_get_store_path"
          # Use sed to replace the placeholder with the actual store number in the processed copy
          sed -i "s/@RETAIL_STORE_ID@/$storeNumber/g" "$processed_get_store_path"
          echo "get_store_processed.json created successfully"
        else
          echo "Warning: get_store.json not found at: $get_store_json_path"
        fi
        
        # Call the store initialization script
        if ! "$store_init_script" --ComponentType "$COMPONENT_TYPE" --base_url "$base_url" --StoreId "$storeNumber" --WorkstationId "$workstationId"; then
          echo "Error during store initialization"
          exit 1
        fi
        echo "Store initialization completed successfully"
      else
        echo "Error: Store initialization script not found at: $store_init_script"
        exit 1
      fi
    else
      echo "Skipping store initialization for WDM component"
    fi
else
    echo "Skipping onboarding and store initialization for update"
fi

# Read onboarding token
onboardingToken=""
if [ "$isUpdate" = false ]; then
    onboardingTokenPath="onboarding.token"
    if [ ! -f "$onboardingTokenPath" ]; then
        echo "Error: Onboarding token file not found at: $onboardingTokenPath"
        exit 1
    fi
    onboardingToken=$(cat "$onboardingTokenPath" | tr -d '\n')
else
    echo "Skipping onboarding token check for update mode"
    onboardingToken="not-required-for-update"
fi

# Create configuration files
cat > "installationtoken.txt" << EOF
configService.url=https://$server/config-service
cims.url=https://$server/cims
station.tenantId=001
station.storeId=$storeNumber
station.workstationId=$workstationId
station.applicationVersion=$component_version
station.systemType=$systemType
onboarding.token=$onboardingToken
dsg.url=https://$dsg_server/dsg/content/cep/SoftwarePackage
EOF

# Create base64 token - ensure it's a single line without line breaks
base64Token=$(base64 -w 0 installationtoken.txt)
echo "$base64Token" > "installationtoken.base64"

# Create addonpack.properties
cat > "$install_dir/addonpack.properties" << EOF
dsg.addonpack.url=https://$dsg_server/dsg/content/cep/AddOnPacks
addonpacks=
EOF

# Handle .p12 file if it exists
p12_files=()
if compgen -G "*.p12" > /dev/null; then
  mapfile -t p12_files < <(ls *.p12 2>/dev/null)
fi

# Create security directory if it doesn't exist
mkdir -p "$security_dir"

# Check for certificates in the security directory
security_p12_files=()
if compgen -G "$security_dir/*.p12" > /dev/null; then
  mapfile -t security_p12_files < <(ls $security_dir/*.p12 2>/dev/null)
fi

ssl_path=""
used_existing_cert=false

# Check if we have certificates in current directory
if [ "${#p12_files[@]}" -gt 0 ]; then
  echo "Found .p12 file(s) in script directory"
  
  # Check if we have certificates in security directory
  if [ "${#security_p12_files[@]}" -gt 0 ]; then
    echo "Found existing certificate(s) in security directory, checking for name matches..."
    
    # Check for name matches
    matching_cert=""
    for p12_file in "${p12_files[@]}"; do
      cert_name=$(basename "$p12_file")
      
      # Check if this certificate name exists in security directory
      for security_cert in "${security_p12_files[@]}"; do
        security_cert_name=$(basename "$security_cert")
        if [ "$cert_name" = "$security_cert_name" ]; then
          matching_cert="$security_cert"
          break 2  # Break out of both loops
        fi
      done
    done
    
    if [ -n "$matching_cert" ]; then
      # Use the matching certificate from security directory
      ssl_path="$matching_cert"
      echo "Using existing certificate with matching name: $(basename "$matching_cert") from security directory"
      used_existing_cert=true
    else
      # No matching certificate found, copy and use the new one
      echo "Certificate in current directory has different name than existing ones, copying and using new certificate"
      
      # Copy the first p12 file found if there are multiple
      new_cert="${p12_files[0]}"
      cert_name=$(basename "$new_cert")
      dest_path="$security_dir/$cert_name"
      echo "Copying $cert_name to $dest_path"
      cp "$new_cert" "$dest_path"
      
      # Use the newly copied certificate
      ssl_path="$dest_path"
    fi
  else
    # No certificates in security directory, copy all from current directory
    echo "No certificates in security directory, copying all from current directory"
    
    # Copy each .p12 file found
    for p12_file in "${p12_files[@]}"; do
      # Copy with original filename
      cert_name=$(basename "$p12_file")
      dest_path="$security_dir/$cert_name"
      echo "Copying $cert_name to $dest_path"
      cp "$p12_file" "$dest_path"
      
      # Set the ssl_path to the first certificate copied
      if [ -z "$ssl_path" ]; then
        ssl_path="$dest_path"
      fi
    done
  fi
elif [ "${#security_p12_files[@]}" -gt 0 ]; then
  # No certificates in current directory but some in security directory
  # Use the first .p12 file found in the security directory
  ssl_path="${security_p12_files[0]}"
  echo "Found certificate at: $ssl_path"
  used_existing_cert=true
else
  # No certificate found anywhere
  echo "Warning: No certificate found for Tomcat. The installation may fail if a certificate is required."
fi

# Paths
launchers_path="$PWD/helper/launchers"

# Verify launchers path exists
if [ ! -d "$launchers_path" ]; then
  echo "Launchers path does not exist: $launchers_path"
  exit 1
fi

# Select the appropriate template file
case "$COMPONENT_TYPE" in
  'POS')
    template_file="$launchers_path/launcher.pos.template"
    ;;
  'WDM')
    template_file="$launchers_path/launcher.wdm.template"
    ;;
  'FLOW-SERVICE')
    template_file="$launchers_path/launcher.flow-service.template"
    ;;
  'LPA-SERVICE')
    template_file="$launchers_path/launcher.lpa-service.template"
    ;;
  'STOREHUB-SERVICE')
    template_file="$launchers_path/launcher.storehub-service.template"
    ;;
  *)
    template_file="$launchers_path/launcher.wdm.template"
    ;;
esac

if [ ! -f "$template_file" ]; then
  echo "Error: Template file $template_file not found"
  exit 1
fi

# Read the template content
launcher_props=$(cat "$template_file")

# Replace placeholders with actual values
launcher_props="${launcher_props//@INSTALL_DIR@/$install_dir}"
launcher_props="${launcher_props//@BASE64_TOKEN@/$base64Token}"
launcher_props="${launcher_props//@OFFLINE_MODE@/$(if [ "$offline_mode" = true ]; then echo "1"; else echo "0"; fi)}"

if [ "$offline_mode" = true ] && [ -n "$jre_version" ]; then
  launcher_props="${launcher_props//@JRE_VERSION@/$jre_version}"
else
  launcher_props="${launcher_props//@JRE_VERSION@/}"
fi

if [ "$offline_mode" = true ] && [ "${#jre_files[@]}" -gt 0 ]; then
  launcher_props="${launcher_props//@JRE_PACKAGE@/$PWD\/${jre_files[0]}}"
else
  launcher_props="${launcher_props//@JRE_PACKAGE@/}"
fi

if [ "$offline_mode" = true ] && [ "$has_installer_jar" = true ]; then
  launcher_props="${launcher_props//@INSTALLER_PACKAGE@/$installer_jar}"
else
  launcher_props="${launcher_props//@INSTALLER_PACKAGE@/}"
fi

launcher_props="${launcher_props//@SSL_PATH@/$ssl_path}"
launcher_props="${launcher_props//@SSL_PASSWORD@/$ssl_password}"

# For StoreHub, set the Firebird server path
# Ensure the path is clean before replacing
if [[ "$COMPONENT_TYPE" == "STOREHUB-SERVICE" ]]; then
  # For Linux, we'll use a fixed path to avoid any issues
  firebird_server_path="/opt/firebird"
  echo "Using fixed Firebird server path for launcher.properties: $firebird_server_path"
  
  # Instead of using string replacement, we'll directly modify the launcher.properties content
  # by removing the existing line and adding a new one
  launcher_props=$(echo "$launcher_props" | grep -v "firebirdServerPath=")
  launcher_props="${launcher_props}"$'\n'"firebirdServerPath=$firebird_server_path"
  
  # Add the Jaybird path only if it was detected
  if [ "$has_jaybird" = true ]; then
    launcher_props=$(echo "$launcher_props" | grep -v "firebird_driver_path_local=")
    launcher_props="${launcher_props}"$'\n'"firebird_driver_path_local=$firebird_driver_path_local"
    echo "Added detected Jaybird driver path to launcher.properties: $firebird_driver_path_local"
  fi
else
  # For other components, use the standard replacement
  launcher_props="${launcher_props///opt/firebird/$firebird_server_path}"
  launcher_props="${launcher_props//@FIREBIRD_DRIVER_PATH_LOCAL@/$firebird_driver_path_local}"
fi

# Add Tomcat replacements if Tomcat files were found
if [ "${#tomcat_files[@]}" -gt 0 ]; then
  if [ "$offline_mode" = true ]; then
    launcher_props="${launcher_props//@TOMCAT_VERSION@/$tomcat_version}"
    launcher_props="${launcher_props//@TOMCAT_PACKAGE@/$PWD\/${tomcat_files[0]}}"
  else
    launcher_props="${launcher_props//@TOMCAT_VERSION@/}"
    launcher_props="${launcher_props//@TOMCAT_PACKAGE@/}"
  fi
fi

echo "Writing launcher properties to file..."
echo "$launcher_props" > "launcher.properties"
echo "Launcher properties file created successfully. Launcher will use this for configuration."

# Download or use local Launcher
if [ "$offline_mode" = false ]; then
  download_url="https://$base_url/dsg/content/cep/SoftwarePackage/$systemType/$component_version/Launcher.run"
  echo "Attempting to download Launcher.run from: $download_url"
  
  # Try using curl with progress bar first
  if command -v curl >/dev/null 2>&1; then
    echo "Using curl for download with progress bar..."
    if curl -L --progress-bar -o "Launcher.run" "$download_url"; then
      if [ -f "Launcher.run" ] && [ -s "Launcher.run" ]; then
        echo "Successfully downloaded Launcher.run using curl"
      else
        echo "Curl download produced empty file. Trying wget..."
        if command -v wget >/dev/null 2>&1; then
          echo "Using wget as fallback..."
          if wget --show-progress -O "Launcher.run" "$download_url"; then
            echo "Successfully downloaded Launcher.run using wget"
          else
            echo "Error downloading Launcher.run"
            exit 1
          fi
        else
          echo "Error downloading: Empty file and wget not available"
          exit 1
        fi
      fi
    else
      # Try wget as a fallback
      echo "Curl failed. Trying wget..."
      if command -v wget >/dev/null 2>&1; then
        echo "Using wget as fallback..."
        if wget --show-progress -O "Launcher.run" "$download_url"; then
          echo "Successfully downloaded Launcher.run using wget"
        else
          echo "Error downloading Launcher.run"
          exit 1
        fi
      else
        echo "Error downloading: Curl failed and wget not available"
        exit 1
      fi
    fi
  elif command -v wget >/dev/null 2>&1; then
    # No curl, use wget directly
    echo "Using wget for download with progress bar..."
    if wget --show-progress -O "Launcher.run" "$download_url"; then
      echo "Successfully downloaded Launcher.run using wget"
    else
      echo "Error downloading Launcher.run"
      exit 1
    fi
  else
    echo "Error: Neither curl nor wget is available for downloading"
    exit 1
  fi
  
  chmod +x "./Launcher.run"
else
  # In offline mode, copy the Launcher from the package directory to the current directory
  echo "Copying Launcher.run from $package_dir to current directory..."
  if ! cp "$launcher_path" "./Launcher.run"; then
    echo "Error copying Launcher.run"
    exit 1
  fi
  echo "Successfully copied Launcher.run"
  chmod +x "./Launcher.run"
fi

# Start the installation
echo "Starting installation..."

# Check if installer log already exists and delete it
installer_log_path="$install_dir/installer/log/installer.log"
if [ -f "$installer_log_path" ]; then
  echo "Found existing installer log file. Deleting to ensure clean installation..."
  rm -f "$installer_log_path" 2>/dev/null
  if [ $? -eq 0 ]; then
    echo "Existing installer log file deleted successfully."
  else
    echo "Warning: Failed to delete existing installer log file."
    echo "This might lead to confusing log output during installation."
  fi
fi

echo "Running Launcher.run with arguments: --defaultsFile launcher.properties --mode unattended"

# If we found JRE, add it to PATH temporarily to ensure Java can be found

# Start Launcher based on whether this is an update or new installation
if [ "$isUpdate" = true ]; then
    echo -e "\033[1;36m=================================================================\033[0m"
    echo -e "\033[1;36m                     RUNNING IN UPDATE MODE                      \033[0m"
    echo -e "\033[1;36m=================================================================\033[0m"
    echo "Running Launcher with update arguments: --mode unattended --forceDownload false --station.applicationVersion $component_version --station.propertiesPath $install_dir"
    ./Launcher.run --mode unattended --forceDownload false --station.applicationVersion "$component_version" --station.propertiesPath "$install_dir" &
    launcher_pid=$!
else
    echo -e "\033[1;32m=================================================================\033[0m"
    echo -e "\033[1;32m                 RUNNING IN FULL INSTALLATION MODE               \033[0m"
    echo -e "\033[1;32m=================================================================\033[0m"
    ./Launcher.run --defaultsFile launcher.properties --mode unattended &
    launcher_pid=$!
fi

# Check installation logs
max_wait_time=7200 # 2 hours timeout
max_log_wait_time=3600 # 1 hour timeout for files download from DSG
elapsed=0
log_wait_elapsed=0
check_interval=2 # Check every 2 seconds
last_line_number=0
first_log=true

echo "Waiting for installation to complete..."
echo "Monitoring log: $installer_log_path"

while [ $elapsed -lt $max_wait_time ]; do
  # Check if launcher is still running
  if ! kill -0 $launcher_pid 2>/dev/null; then
    launcher_exit_code=$?
    echo "Launcher process has exited with code: $launcher_exit_code"
    echo "Continuing to monitor logs for 5 seconds..."
    
    post_exit_time=5
    while [ $post_exit_time -gt 0 ]; do
      if [ -f "$installer_log_path" ]; then
        # Read new lines from the log
        current_content=$(cat "$installer_log_path" 2>/dev/null || echo "")
        current_line_count=$(echo "$current_content" | wc -l)
        
        if [ $current_line_count -gt $last_line_number ]; then
          new_lines=$(echo "$current_content" | tail -n $((current_line_count - last_line_number)))
          echo "$new_lines" | while read -r line; do
            echo "LOG: $line"
          done
          last_line_number=$current_line_count
        fi
      fi
      
      echo -n -e "\rTime remaining for log monitoring: $post_exit_time seconds..."
      sleep 1
      post_exit_time=$((post_exit_time - 1))
    done
    echo -e "\nCompleting installation..."
    
    # Final log check
    if [ -f "$installer_log_path" ]; then
      final_log_content=$(tail -n 20 "$installer_log_path" 2>/dev/null || echo "")
      
      if echo "$final_log_content" | grep -q "Installation finished successfully"; then
        echo "Installation completed successfully!"
        echo "Installation directory: $install_dir"
        
        # Component-specific completion messages
        if [ "$COMPONENT_TYPE" = "WDM" ]; then
          echo "WDM installation completed. Please check the following:"
          echo "1. Tomcat service status"
          echo "2. WDM application accessibility at https://localhost:8543"
        else
          echo "$COMPONENT_TYPE installation completed. Please check the application status."
        fi
        
        # Cleanup: Move generated files to a results directory
        results_dir="results_$COMPONENT_TYPE"
        echo "Performing cleanup - Moving generated files to $results_dir directory..."
        
        # Create the results directory if it doesn't exist
        mkdir -p "$results_dir"
        
        # List of files to move
        files_to_move=(
          "installationtoken.txt"
          "installationtoken.base64"
          "launcher.properties"
          "onboarding.token"
          "Launcher.run"
        )
        
        # Add log files
        log_files=$(find . -maxdepth 1 -name "*.log" -type f 2>/dev/null || echo "")
        # Only add log files if they actually exist
        if [ -n "$log_files" ]; then
          for log_file in $log_files; do
            if [ -f "$log_file" ]; then
              files_to_move+=("$log_file")
            fi
          done
        fi
        
        # Find all JSON files in the current directory only
        json_files=$(find . -maxdepth 1 -name "*.json" -type f 2>/dev/null || echo "")
        if [ -n "$json_files" ]; then
          echo "Found JSON files to move"
          for json_file in $json_files; do
            files_to_move+=("$json_file")
          done
        else
          echo "No JSON files need to be cleaned up"
        fi
        
        # Move each file to the results directory
        for file in "${files_to_move[@]}"; do
          if [ -f "$file" ]; then
            # Skip files in helper directory
            if [[ "$file" == *"/helper/"* ]]; then
              continue
            fi
            
            # Process only files in current directory
            filename=$(basename "$file")
            dest_file="$results_dir/$filename"
            
            # Copy file to results directory then remove original
            cp "$file" "$dest_file" 2>/dev/null
            if [ $? -eq 0 ]; then
              echo "Moved: $file to $dest_file"
              rm "$file"
            else
              echo "Warning: Could not move $file to results directory"
            fi
          fi
        done
        
        # Make sure the log file is moved to results directory at the end
        if [ -f "$log_file" ]; then
            dest_log_file="$results_dir/$log_file"
            cp "$log_file" "$dest_log_file" 2>/dev/null
            if [ $? -eq 0 ]; then
                echo "Console output log saved to: $dest_log_file"
                rm "$log_file"
            else
                echo "Warning: Could not move log file to results directory"
            fi
        fi
        
        echo "Cleanup completed. Installation files have been moved to $results_dir directory."
        exit 0
      elif echo "$final_log_content" | grep -q "Installation failed"; then
        echo "Installation failed. Please check the logs at: $installer_log_path"
        exit 1
      fi
    fi
    
    # If we couldn't determine status from logs, use process exit code
    if [ $launcher_exit_code -eq 0 ]; then
      echo "Launcher completed successfully based on exit code."
      echo "Installation directory: $install_dir"
      
      # Cleanup: Move generated files to a results directory
      results_dir="results_$COMPONENT_TYPE"
      echo "Performing cleanup - Moving generated files to $results_dir directory..."
      
      # Create the results directory if it doesn't exist
      mkdir -p "$results_dir"
      
      # List of files to move
      files_to_move=(
        "installationtoken.txt"
        "installationtoken.base64"
        "launcher.properties"
        "onboarding.token"
        "Launcher.run"
      )
      
      # Add log files
      log_files=$(find . -maxdepth 1 -name "*.log" -type f 2>/dev/null || echo "")
      # Only add log files if they actually exist
      if [ -n "$log_files" ]; then
        for log_file in $log_files; do
          if [ -f "$log_file" ]; then
            files_to_move+=("$log_file")
          fi
        done
      fi
      
      # Find all JSON files in the current directory only
      json_files=$(find . -maxdepth 1 -name "*.json" -type f 2>/dev/null || echo "")
      if [ -n "$json_files" ]; then
        echo "Found JSON files to move"
        for json_file in $json_files; do
          files_to_move+=("$json_file")
        done
      else
        echo "No JSON files need to be cleaned up"
      fi
      
      # Move each file to the results directory
      for file in "${files_to_move[@]}"; do
        if [ -f "$file" ]; then
          # Skip files in helper directory
          if [[ "$file" == *"/helper/"* ]]; then
            continue
          fi
          
          # Process only files in current directory
          filename=$(basename "$file")
          dest_file="$results_dir/$filename"
          
          # Copy file to results directory then remove original
          cp "$file" "$dest_file" 2>/dev/null
          if [ $? -eq 0 ]; then
            echo "Moved: $file to $dest_file"
            rm "$file"
          else
            echo "Warning: Could not move $file to results directory"
          fi
        fi
      done
      
      # Make sure the log file is moved to results directory at the end
      if [ -f "$log_file" ]; then
          dest_log_file="$results_dir/$log_file"
          cp "$log_file" "$dest_log_file" 2>/dev/null
          if [ $? -eq 0 ]; then
              echo "Console output log saved to: $dest_log_file"
              rm "$log_file"
          else
              echo "Warning: Could not move log file to results directory"
          fi
      fi
      
      echo "Cleanup completed. Installation files have been moved to $results_dir directory."
      exit 0
    else
      echo "Launcher failed with exit code: $launcher_exit_code"
      echo "Please check the logs at: $installer_log_path"
      
      # Cleanup for failed installation
      errors_dir="errors_$COMPONENT_TYPE"
      echo "Performing cleanup for failed installation - Moving files to $errors_dir directory..."
      
      # Create the errors directory if it doesn't exist
      mkdir -p "$errors_dir"
      
      # List of files to move
      files_to_move=(
        "installationtoken.txt"
        "installationtoken.base64"
        "launcher.properties"
        "onboarding.token"
        "Launcher.run"
      )
      
      # Add log files
      log_files=$(find . -maxdepth 1 -name "*.log" -type f 2>/dev/null || echo "")
      # Only add log files if they actually exist
      if [ -n "$log_files" ]; then
        for log_file in $log_files; do
          if [ -f "$log_file" ]; then
            files_to_move+=("$log_file")
          fi
        done
      fi
      
      # Find all JSON files in the current directory only
      json_files=$(find . -maxdepth 1 -name "*.json" -type f 2>/dev/null || echo "")
      if [ -n "$json_files" ]; then
        echo "Found JSON files to move"
        for json_file in $json_files; do
          files_to_move+=("$json_file")
        done
      else
        echo "No JSON files need to be cleaned up"
      fi
      
      # Move each file to the errors directory
      for file in "${files_to_move[@]}"; do
        if [ -f "$file" ]; then
          # Skip files in helper directory
          if [[ "$file" == *"/helper/"* ]]; then
            continue
          fi
          
          # Process only files in current directory
          filename=$(basename "$file")
          dest_file="$errors_dir/$filename"
          
          # Copy file to errors directory then remove original
          cp "$file" "$dest_file" 2>/dev/null
          if [ $? -eq 0 ]; then
            echo "Moved: $file to $dest_file"
            rm "$file"
          else
            echo "Warning: Could not move $file to errors directory"
          fi
        fi
      done
      
      # Make sure the log file is moved to errors directory at the end
      if [ -f "$log_file" ]; then
          dest_log_file="$errors_dir/$log_file"
          cp "$log_file" "$dest_log_file" 2>/dev/null
          if [ $? -eq 0 ]; then
              echo "Console output log saved to: $dest_log_file"
              rm "$log_file"
          else
              echo "Warning: Could not move log file to errors directory"
          fi
      fi
      
      echo "Cleanup completed. Failed installation files have been moved to $errors_dir directory."
      exit 1
    fi
  fi

  if [ -f "$installer_log_path" ]; then
    # First time we see the log file
    if [ "$first_log" = true ]; then
      echo "Log file created at: $installer_log_path"
      first_log=false
    fi

    # Read new lines from the log
    current_content=$(cat "$installer_log_path" 2>/dev/null || echo "")
    current_line_count=$(echo "$current_content" | wc -l)
    
    if [ $current_line_count -gt $last_line_number ]; then
      new_lines=$(echo "$current_content" | tail -n $((current_line_count - last_line_number)))
      echo "$new_lines" | while read -r line; do
        echo "LOG: $line"
      done
      last_line_number=$current_line_count
    fi

    # Check for completion
    log_content=$(tail -n 20 "$installer_log_path" 2>/dev/null || echo "")
    
    if echo "$log_content" | grep -q "Installation finished successfully"; then
      echo "Installation completed successfully!"
      echo "Installation directory: $install_dir"
      
      # Component-specific completion messages
      if [ "$COMPONENT_TYPE" = "WDM" ]; then
        echo "WDM installation completed. Please check the following:"
        echo "1. Tomcat service status"
        echo "2. WDM application accessibility at https://localhost:8543"
      else
        echo "$COMPONENT_TYPE installation completed. Please check the application status."
      fi
      
      # Kill the launcher process if it's still running
      if kill -0 $launcher_pid 2>/dev/null; then
        kill $launcher_pid
      fi
      
      # Cleanup: Move generated files to a results directory
      results_dir="results_$COMPONENT_TYPE"
      echo "Performing cleanup - Moving generated files to $results_dir directory..."
      
      # Create the results directory if it doesn't exist
      mkdir -p "$results_dir"
      
      # List of files to move
      files_to_move=(
        "installationtoken.txt"
        "installationtoken.base64"
        "launcher.properties"
        "onboarding.token"
        "Launcher.run"
      )
      
      # Add log files
      log_files=$(find . -maxdepth 1 -name "*.log" -type f 2>/dev/null || echo "")
      # Only add log files if they actually exist
      if [ -n "$log_files" ]; then
        for log_file in $log_files; do
          if [ -f "$log_file" ]; then
            files_to_move+=("$log_file")
          fi
        done
      fi
      
      # Find all JSON files in the current directory only
      json_files=$(find . -maxdepth 1 -name "*.json" -type f 2>/dev/null || echo "")
      if [ -n "$json_files" ]; then
        echo "Found JSON files to move"
        for json_file in $json_files; do
          files_to_move+=("$json_file")
        done
      else
        echo "No JSON files need to be cleaned up"
      fi
      
      # Move each file to the results directory
      for file in "${files_to_move[@]}"; do
        if [ -f "$file" ]; then
          # Skip files in helper directory
          if [[ "$file" == *"/helper/"* ]]; then
            continue
          fi
          
          # Process only files in current directory
          filename=$(basename "$file")
          dest_file="$results_dir/$filename"
          
          # Copy file to results directory then remove original
          cp "$file" "$dest_file" 2>/dev/null
          if [ $? -eq 0 ]; then
            echo "Moved: $file to $dest_file"
            rm "$file"
          else
            echo "Warning: Could not move $file to results directory"
          fi
        fi
      done
      
      # Make sure the log file is moved to results directory at the end
      if [ -f "$log_file" ]; then
          dest_log_file="$results_dir/$log_file"
          cp "$log_file" "$dest_log_file" 2>/dev/null
          if [ $? -eq 0 ]; then
              echo "Console output log saved to: $dest_log_file"
              rm "$log_file"
          else
              echo "Warning: Could not move log file to results directory"
          fi
      fi
      
      echo "Cleanup completed. Installation files have been moved to $results_dir directory."
      exit 0
    elif echo "$log_content" | grep -q "Installation failed"; then
      echo "Installation failed. Please check the logs at: $installer_log_path"
      
      # Kill the launcher process if it's still running
      if kill -0 $launcher_pid 2>/dev/null; then
        kill $launcher_pid
      fi
      
      # Cleanup for failed installation
      errors_dir="errors_$COMPONENT_TYPE"
      echo "Performing cleanup for failed installation - Moving files to $errors_dir directory..."
      
      # Create the errors directory if it doesn't exist
      mkdir -p "$errors_dir"
      
      # List of files to move
      files_to_move=(
        "installationtoken.txt"
        "installationtoken.base64"
        "launcher.properties"
        "onboarding.token"
        "Launcher.run"
      )
      
      # Add log files
      log_files=$(find . -maxdepth 1 -name "*.log" -type f 2>/dev/null || echo "")
      # Only add log files if they actually exist
      if [ -n "$log_files" ]; then
        for log_file in $log_files; do
          if [ -f "$log_file" ]; then
            files_to_move+=("$log_file")
          fi
        done
      fi
      
      # Find all JSON files in the current directory only
      json_files=$(find . -maxdepth 1 -name "*.json" -type f 2>/dev/null || echo "")
      if [ -n "$json_files" ]; then
        echo "Found JSON files to move"
        for json_file in $json_files; do
          files_to_move+=("$json_file")
        done
      else
        echo "No JSON files need to be cleaned up"
      fi
      
      # Move each file to the errors directory
      for file in "${files_to_move[@]}"; do
        if [ -f "$file" ]; then
          # Skip files in helper directory
          if [[ "$file" == *"/helper/"* ]]; then
            continue
          fi
          
          # Process only files in current directory
          filename=$(basename "$file")
          dest_file="$errors_dir/$filename"
          
          # Copy file to errors directory then remove original
          cp "$file" "$dest_file" 2>/dev/null
          if [ $? -eq 0 ]; then
            echo "Moved: $file to $dest_file"
            rm "$file"
          else
            echo "Warning: Could not move $file to errors directory"
          fi
        fi
      done
      
      # Make sure the log file is moved to errors directory at the end
      if [ -f "$log_file" ]; then
          dest_log_file="$errors_dir/$log_file"
          cp "$log_file" "$dest_log_file" 2>/dev/null
          if [ $? -eq 0 ]; then
              echo "Console output log saved to: $dest_log_file"
              rm "$log_file"
          else
              echo "Warning: Could not move log file to errors directory"
          fi
      fi
      
      echo "Cleanup completed. Failed installation files have been moved to $errors_dir directory."
      exit 1
    fi
  else
    if [ "$offline_mode" = false ]; then
      echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed) - Downloading installation files from $base_url DSG"
    else
      echo "Waiting for installer log file to be created... ($log_wait_elapsed seconds elapsed)"
    fi
    log_wait_elapsed=$((log_wait_elapsed + check_interval))
    if [ $log_wait_elapsed -ge $max_log_wait_time ]; then
      echo "Error: Timeout waiting for installer log file to be created after $((max_log_wait_time/60)) minutes"
      echo "Expected log path: $installer_log_path"
      # Try to kill launcher process if it's still running
      if kill -0 $launcher_pid 2>/dev/null; then
        echo "Terminating launcher process..."
        kill $launcher_pid
      fi
      exit 1
    fi
  fi
  
  sleep $check_interval
  elapsed=$((elapsed + check_interval))
  
  # Show progress less frequently
  if [ $((elapsed % 30)) -eq 0 ]; then
    echo "Installation in progress... ($((elapsed / 60)) minutes elapsed)"
  fi
done

# Try to kill launcher process if it's still running after timeout
if kill -0 $launcher_pid 2>/dev/null; then
  echo "Terminating launcher process due to timeout..."
  kill $launcher_pid
fi

echo "Warning: Installation timeout reached after 2 hours. Please check the installation logs at: $installer_log_path"
echo "Installation directory: $install_dir"

# Cleanup for timeout failure
errors_dir="errors_$COMPONENT_TYPE"
echo "Performing cleanup for timed out installation - Moving files to $errors_dir directory..."

# Create the errors directory if it doesn't exist
mkdir -p "$errors_dir"

# List of files to move
files_to_move=(
  "installationtoken.txt"
  "installationtoken.base64"
  "launcher.properties"
  "onboarding.token"
  "Launcher.run"
)

# Add log files
log_files=$(find . -maxdepth 1 -name "*.log" -type f 2>/dev/null || echo "")
# Only add log files if they actually exist
if [ -n "$log_files" ]; then
  for log_file in $log_files; do
    if [ -f "$log_file" ]; then
      files_to_move+=("$log_file")
    fi
  done
fi

# Find all JSON files in the current directory only
json_files=$(find . -maxdepth 1 -name "*.json" -type f 2>/dev/null || echo "")
if [ -n "$json_files" ]; then
  echo "Found JSON files to move"
  for json_file in $json_files; do
    files_to_move+=("$json_file")
  done
else
  echo "No JSON files need to be cleaned up"
fi

# Move each file to the errors directory
for file in "${files_to_move[@]}"; do
  if [ -f "$file" ]; then
    # Skip files in helper directory
    if [[ "$file" == *"/helper/"* ]]; then
      continue
    fi
    
    # Process only files in current directory
    filename=$(basename "$file")
    dest_file="$errors_dir/$filename"
    
    # Copy file to errors directory then remove original
    cp "$file" "$dest_file" 2>/dev/null
    if [ $? -eq 0 ]; then
      echo "Moved: $file to $dest_file"
      rm "$file"
    else
      echo "Warning: Could not move $file to errors directory"
    fi
  fi
done

# Make sure the log file is moved to errors directory at the end
if [ -f "$log_file" ]; then
    dest_log_file="$errors_dir/$log_file"
    cp "$log_file" "$dest_log_file" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "Console output log saved to: $dest_log_file"
        rm "$log_file"
    else
        echo "Warning: Could not move log file to errors directory"
    fi
fi

echo "Cleanup completed. Timed out installation files have been moved to $errors_dir directory."
exit 1 