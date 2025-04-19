param(
    [switch]$offline,
    [ValidateSet('POS', 'WDM', 'FLOW-SERVICE', 'LPA', 'SH', 'LPA-SERVICE', 'STOREHUB-SERVICE')]
    [string]$ComponentType = 'POS',
    [string]$base_url = "example.cloud4retail.co",
    [string]$storeId  # Will be determined by hostname detection or user input
)

# Create a unique log filename based on timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "GKInstall_$ComponentType`_$timestamp.log"

# Start transcript to capture all console output
try {
    Start-Transcript -Path $logFile -Append
    Write-Host "Console output is being saved to $logFile"
} catch {
    Write-Host "Warning: Unable to start transcript. Console output will not be saved to a log file."
    Write-Host "Error: $_"
}

# Define function to ensure transcript is stopped
function Stop-TranscriptSafely {
    # Simplified approach - just call Stop-Transcript directly
    try {
        Stop-Transcript -ErrorAction SilentlyContinue
    } catch {
        # Ignore errors
    }
}

# Set certificate validation to always return true (bypass SSL validation)
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}

# Stop on first error
$ErrorActionPreference = "Stop"

# Map shortened component types to full names
if ($ComponentType -eq 'LPA') {
    $ComponentType = 'LPA-SERVICE'
} elseif ($ComponentType -eq 'SH') {
    $ComponentType = 'STOREHUB-SERVICE'
}

# Function for error handling
function Handle-Error {
    param($LineNumber)
    Write-Host "Error occurred at line $LineNumber"
    exit 1
}

# Function to extract version from any package filename
function Get-PackageVersion {
    param(
        [string]$PackageFile,
        [string]$ComponentPrefix
    )
    
    # Get filename without extension
    $filename = [System.IO.Path]::GetFileNameWithoutExtension($PackageFile)
    
    # Try different patterns to extract version
    
    # Pattern 1: prefix-1.2.3 (standard format)
    if ($filename -match "^$ComponentPrefix-(\d+(\.\d+)*)$") {
        return $matches[1]
    }
    
    # Pattern 2: prefix-1.2.3-suffix (with additional info)
    if ($filename -match "^$ComponentPrefix-(\d+(\.\d+)*)-") {
        return $matches[1]
    }
    
    # Pattern 3: prefix_1_2_3 (underscore format)
    if ($filename -match "^$ComponentPrefix[_-](\d+)[_\.](\d+)[_\.](\d+)") {
        return "$($matches[1]).$($matches[2]).$($matches[3])"
    }
    
    # Pattern 4: prefix1.2.3 (no separator)
    if ($filename -match "^$ComponentPrefix(\d+(\.\d+)*)$") {
        return $matches[1]
    }
    
    # Pattern 5: just extract any sequence of numbers and dots
    if ($filename -match '(\d+(\.\d+)*)') {
        return $matches[1]
    }
    
    # If no pattern matches, return the original filename without prefix
    $version = $filename -replace "^$ComponentPrefix-",''
    if ([string]::IsNullOrEmpty($version)) {
        Write-Host "Error: Could not extract version from filename $PackageFile"
        return $null
    }
    return $version
}

# Function to get JRE version from filename
function Get-JreVersion {
    param($JreZip)
    
    # Get filename without extension
    $filename = [System.IO.Path]::GetFileNameWithoutExtension($JreZip)
    
    # Special case for Java_zulujre pattern
    if ($filename -match "Java_zulujre.*?[-_](\d+\.\d+\.\d+)") {
        Write-Host "Detected Java version $($matches[1]) from Zulu JRE filename"
        return $matches[1]
    }
    
    # Special case for x64/x86 in filename to avoid extracting "64" as version
    if ($filename -match "x64-(\d+\.\d+\.\d+)") {
        Write-Host "Detected Java version $($matches[1]) from x64 pattern"
        return $matches[1]
    }
    if ($filename -match "x86-(\d+\.\d+\.\d+)") {
        Write-Host "Detected Java version $($matches[1]) from x86 pattern"
        return $matches[1]
    }
    
    # Try jre prefix first, then java if that fails
    $version = Get-PackageVersion -PackageFile $JreZip -ComponentPrefix "jre"
    if ([string]::IsNullOrEmpty($version)) {
        $version = Get-PackageVersion -PackageFile $JreZip -ComponentPrefix "java"
    }
    
    # Validate version format - if it's just a number like "64", it's probably wrong
    if ($version -match "^\d+$" -and $filename -match "(\d+\.\d+\.\d+)") {
        # Extract version with format like 11.0.18
        Write-Host "Correcting invalid version '$version' to $($matches[1])"
        return $matches[1]
    }
    
    return $version
}

# Function to get Tomcat version from filename
function Get-TomcatVersion {
    param($TomcatZip)
    return Get-PackageVersion -PackageFile $TomcatZip -ComponentPrefix "tomcat"
}

# Update these lines to use the base_url
$server = $base_url
$dsg_server = $base_url

# Basic configuration
$version = "v1.0.0"
$base_install_dir = "C:\gkretail"

# Set component-specific configurations
$systemType = switch ($ComponentType) {
    'POS' { "CLOUD4RETAIL-OPOS-CLOUD" }
    'WDM' { "CLOUD4RETAIL-wdm" }
    'FLOW-SERVICE' { "GKR-FLOWSERVICE-CLOUD" }
    'LPA-SERVICE' { "CLOUD4RETAIL-lps-lpa" }
    'STOREHUB-SERVICE' { "CLOUD4RETAIL-sh-cloud" }
    default { "CLOUD4RETAIL-OPOS-CLOUD" }
}

# Set component-specific version if available
$component_version = switch ($systemType) {
    "CLOUD4RETAIL-OPOS-CLOUD" { "v1.0.0" }
    "CLOUD4RETAIL-wdm" { "v1.0.0" }
    "GKR-FLOWSERVICE-CLOUD" { "v1.0.0" }
    "CLOUD4RETAIL-lps-lpa" { "v1.0.0" }
    "CLOUD4RETAIL-sh-cloud" { "v1.0.0" }
    default { "" }
}

# If component version is empty, use default version
if ([string]::IsNullOrEmpty($component_version)) {
    $component_version = $version
}

$install_dir = Join-Path $base_install_dir $(
    if ($ComponentType -eq 'POS') { "pos-full" } 
    elseif ($ComponentType -eq 'WDM') { "wdm" }
    elseif ($ComponentType -eq 'FLOW-SERVICE') { "flow-service" }
    elseif ($ComponentType -eq 'LPA-SERVICE') { "lpa-service" }
    elseif ($ComponentType -eq 'STOREHUB-SERVICE') { "storehub-service" }
    else { "wdm" }
)

# Initialize offline variables
$jre_version = ""
$jre_file = ""
$tomcat_version = ""
$tomcat_file = ""

# Set WDM SSL settings based on base install directory
$security_dir = Join-Path $base_install_dir "security"
# We'll find the actual certificate file dynamically later
$ssl_password = "changeit"

# For StoreHub, set the Firebird server path
$firebird_server_path = "C:\Program Files\Firebird\Firebird_3_0"
# If the placeholder wasn't replaced (still contains @), use a default value
if ($firebird_server_path -like "*@*") {
    $firebird_server_path = "C:\Program Files\Firebird\Firebird_3_0"
    Write-Host "Using default Firebird server path: $firebird_server_path"
}

# For StoreHub, set the Jaybird driver path
$firebird_driver_path_local = "@FIREBIRD_DRIVER_PATH_LOCAL@"
# If the placeholder wasn't replaced (still contains @), use a default value
if ($firebird_driver_path_local -like "*@*") {
    $firebird_driver_path_local = ""
    Write-Host "No default Jaybird driver path set - will detect during installation if available"
}

# Check offline mode
$offline_mode = $offline.IsPresent

# Validate WDM-specific parameters
if ($ComponentType -eq 'WDM') {
    if ([string]::IsNullOrEmpty($ssl_password)) {
        Write-Host "Error: ssl_password is required for WDM installation"
        exit 1
    }
}

# Add component-specific package directory check
$package_dir = if ($ComponentType -eq 'LPA-SERVICE') { "offline_package_LPA" }
               elseif ($ComponentType -eq 'STOREHUB-SERVICE') { "offline_package_SH" }
               else { "offline_package_$ComponentType" }

# Update offline mode checks
if ($offline.IsPresent) {
    # Check for component-specific offline package
    if (-not (Test-Path $package_dir)) {
        Write-Host "Error: Offline package directory not found: $package_dir"
        exit 1
    }

    # Check for required files based on component type
    if ($ComponentType -eq 'WDM') {
        # Find JRE and Tomcat packages from dedicated Java and Tomcat directories
        $jre_files = @(Get-ChildItem -Path "Java\*.zip" -ErrorAction SilentlyContinue)
        
        # If no jre files found, try more generic patterns
        if ($jre_files.Count -eq 0) {
            $jre_files = @(Get-ChildItem -Path "Java\*jre*.zip" -ErrorAction SilentlyContinue)
            if ($jre_files.Count -eq 0) {
                $jre_files = @(Get-ChildItem -Path "Java\*java*.zip" -ErrorAction SilentlyContinue)
            }
        }
        
        $tomcat_files = @(Get-ChildItem -Path "Tomcat\*.zip" -ErrorAction SilentlyContinue)
        
        # If no tomcat files found, try a more generic pattern
        if ($tomcat_files.Count -eq 0) {
            $tomcat_files = @(Get-ChildItem -Path "Tomcat\*tomcat*.zip" -ErrorAction SilentlyContinue)
        }
        
        # Look for any JAR file to use as installer in the component directory
        $jar_files = @(Get-ChildItem -Path (Join-Path $package_dir "*.jar") -ErrorAction SilentlyContinue)
        $installer_jar = $null
        $has_installer_jar = $false
        
        if ($jar_files.Count -gt 0) {
            if ($jar_files.Count -gt 1) {
                Write-Host "Warning: Multiple JAR files found in $package_dir. Using the first one: $($jar_files[0].Name)"
            }
            $installer_jar = $jar_files[0].FullName
            $has_installer_jar = $true
            Write-Host "Found installer JAR: $($jar_files[0].Name)"
        }
        
        if ($jre_files.Count -eq 0) {
            Write-Host "Error: No JRE/Java package found in Java directory"
            exit 1
        }
        
        if ($tomcat_files.Count -eq 0) {
            Write-Host "Error: No Tomcat package found in Tomcat directory"
            exit 1
        }
        
        # Use the first matching file if multiple are found
        $jre_file = $jre_files[0].FullName
        $tomcat_file = $tomcat_files[0].FullName
        
        # Extract versions
        $jre_version = Get-JreVersion -JreZip $jre_files[0].Name
        $tomcat_version = Get-TomcatVersion -TomcatZip $tomcat_files[0].Name
        
        Write-Host "Found JRE/Java package: $($jre_files[0].Name), version: $jre_version"
        Write-Host "Found Tomcat package: $($tomcat_files[0].Name), version: $tomcat_version"
        
        $required_files = @(
            (Join-Path $package_dir "Launcher.exe"),
            $jre_file,
            $tomcat_file
        )
        
        # Add installer.jar to required files if it exists
        if ($has_installer_jar) {
            $required_files += $installer_jar
        }
    } elseif ($ComponentType -eq 'STOREHUB-SERVICE') {
        # For StoreHub components - with Jaybird support
        # Find JRE and Tomcat packages from dedicated Java and Tomcat directories
        $jre_files = @(Get-ChildItem -Path "Java\*.zip" -ErrorAction SilentlyContinue)
        
        # If no jre files found, try more generic patterns
        if ($jre_files.Count -eq 0) {
            $jre_files = @(Get-ChildItem -Path "Java\*jre*.zip" -ErrorAction SilentlyContinue)
            if ($jre_files.Count -eq 0) {
                $jre_files = @(Get-ChildItem -Path "Java\*java*.zip" -ErrorAction SilentlyContinue)
            }
        }
        
        $tomcat_files = @(Get-ChildItem -Path "Tomcat\*.zip" -ErrorAction SilentlyContinue)
        
        # If no tomcat files found, try a more generic pattern
        if ($tomcat_files.Count -eq 0) {
            $tomcat_files = @(Get-ChildItem -Path "Tomcat\*tomcat*.zip" -ErrorAction SilentlyContinue)
        }
        
        # Look for Jaybird JAR files
        $jaybird_files = @(Get-ChildItem -Path "Jaybird\*.jar" -ErrorAction SilentlyContinue)
        $jaybird_file = $null
        $has_jaybird = $false
        
        if ($jaybird_files.Count -gt 0) {
            if ($jaybird_files.Count -gt 1) {
                Write-Host "Warning: Multiple Jaybird JAR files found. Using the first one: $($jaybird_files[0].Name)"
            }
            $jaybird_file = $jaybird_files[0].FullName
            $has_jaybird = $true
            Write-Host "Found Jaybird driver: $($jaybird_files[0].Name)"
            
            # Update the firebird_driver_path_local to point to the actual JAR file, not just the directory
            $firebird_driver_path_local = $jaybird_file
            Write-Host "Updated Jaybird driver path to: $firebird_driver_path_local"
        } else {
            Write-Host "Warning: No Jaybird driver found in Jaybird directory"
        }
        
        # Look for any JAR file to use as installer in the component directory
        $jar_files = @(Get-ChildItem -Path (Join-Path $package_dir "*.jar") -ErrorAction SilentlyContinue)
        $installer_jar = $null
        $has_installer_jar = $false
        
        if ($jar_files.Count -gt 0) {
            if ($jar_files.Count -gt 1) {
                Write-Host "Warning: Multiple JAR files found in $package_dir. Using the first one: $($jar_files[0].Name)"
            }
            $installer_jar = $jar_files[0].FullName
            $has_installer_jar = $true
            Write-Host "Found installer JAR: $($jar_files[0].Name)"
        }
        
        # Initialize required files with Launcher.exe
        $required_files = @(
            (Join-Path $package_dir "Launcher.exe")
        )
        
        # Process JRE files if available
        if ($jre_files.Count -gt 0) {
            $jre_file = $jre_files[0].FullName
            $jre_version = Get-JreVersion -JreZip $jre_files[0].Name
            Write-Host "Found JRE/Java package: $($jre_files[0].Name), version: $jre_version"
            $required_files += $jre_file
        } else {
            Write-Host "Error: No JRE/Java package found for $ComponentType"
            exit 1
        }
        
        # Process Tomcat files if available
        if ($tomcat_files.Count -gt 0) {
            $tomcat_file = $tomcat_files[0].FullName
            $tomcat_version = Get-TomcatVersion -TomcatZip $tomcat_files[0].Name
            Write-Host "Found Tomcat package: $($tomcat_files[0].Name), version: $tomcat_version"
            $required_files += $tomcat_file
        } else {
            Write-Host "Error: No Tomcat package found for $ComponentType"
            exit 1
        }
        
        # Add Jaybird file to required files if it exists
        if ($has_jaybird) {
            $required_files += $jaybird_file
        }
        
        # Add installer.jar to required files if it exists
        if ($has_installer_jar) {
            $required_files += $installer_jar
        }
    } else {
        # For other components - generic approach with improved detection
        # Find JRE and Tomcat packages from dedicated Java and Tomcat directories
        $jre_files = @(Get-ChildItem -Path "Java\*.zip" -ErrorAction SilentlyContinue)
        
        # If no jre files found, try more generic patterns
        if ($jre_files.Count -eq 0) {
            $jre_files = @(Get-ChildItem -Path "Java\*jre*.zip" -ErrorAction SilentlyContinue)
            if ($jre_files.Count -eq 0) {
                $jre_files = @(Get-ChildItem -Path "Java\*java*.zip" -ErrorAction SilentlyContinue)
            }
        }
        
        $tomcat_files = @(Get-ChildItem -Path "Tomcat\*.zip" -ErrorAction SilentlyContinue)
        
        # If no tomcat files found, try a more generic pattern
        if ($tomcat_files.Count -eq 0) {
            $tomcat_files = @(Get-ChildItem -Path "Tomcat\*tomcat*.zip" -ErrorAction SilentlyContinue)
        }
        
        # Look for any JAR file to use as installer in the component directory
        $jar_files = @(Get-ChildItem -Path (Join-Path $package_dir "*.jar") -ErrorAction SilentlyContinue)
        $installer_jar = $null
        $has_installer_jar = $false
        
        if ($jar_files.Count -gt 0) {
            if ($jar_files.Count -gt 1) {
                Write-Host "Warning: Multiple JAR files found in $package_dir. Using the first one: $($jar_files[0].Name)"
            }
            $installer_jar = $jar_files[0].FullName
            $has_installer_jar = $true
            Write-Host "Found installer JAR: $($jar_files[0].Name)"
        }
        
        # Initialize required files with Launcher.exe
        $required_files = @(
            (Join-Path $package_dir "Launcher.exe")
        )
        
        # Process JRE files if available
        if ($jre_files.Count -gt 0) {
            $jre_file = $jre_files[0].FullName
            $jre_version = Get-JreVersion -JreZip $jre_files[0].Name
            Write-Host "Found JRE/Java package: $($jre_files[0].Name), version: $jre_version"
            $required_files += $jre_file
        } else {
            Write-Host "No JRE/Java package found for $ComponentType."
        }
        
        # Process Tomcat files if available
        if ($tomcat_files.Count -gt 0) {
            $tomcat_file = $tomcat_files[0].FullName
            $tomcat_version = Get-TomcatVersion -TomcatZip $tomcat_files[0].Name
            Write-Host "Found Tomcat package: $($tomcat_files[0].Name), version: $tomcat_version"
            $required_files += $tomcat_file
        } else {
            Write-Host "No Tomcat package found for $ComponentType."
        }
        
        # Add installer.jar to required files if it exists
        if ($has_installer_jar) {
            $required_files += $installer_jar
        }
    }

    foreach ($file in $required_files) {
        if (-not (Test-Path $file)) {
            Write-Host "Error: Required file not found: $file"
            exit 1
        }
    }

    # Update file paths to use component-specific directory
    $launcher_path = Join-Path $package_dir "Launcher.exe"
    # JRE and Tomcat files are already set in the dynamic detection code above
}

# Create installation directory if it doesn't exist
if (-not (Test-Path $install_dir)) {
    New-Item -ItemType Directory -Path $install_dir -Force
}

# Check if this is an update of an existing installation
$isUpdate = $false
if (Test-Path $install_dir) {
    # Check for log folders
    $logPath = Join-Path $install_dir "log"
    $logsPath = Join-Path $install_dir "logs"
    
    # Determine which log folder exists
    $logFolderPath = $null
    if (Test-Path $logPath) {
        $logFolderPath = $logPath
    } elseif (Test-Path $logsPath) {
        $logFolderPath = $logsPath
    }
    
    # If a log folder exists, check for recent activity (last 7 days)
    if ($logFolderPath) {
        Write-Host "Found existing installation at $install_dir with log folder at $logFolderPath"
        
        try {
            $recentFiles = Get-ChildItem -Path $logFolderPath -Recurse -File | 
                           Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-7) }
            
            if ($recentFiles.Count -gt 0) {
                Write-Host "Found $($recentFiles.Count) recently modified log files (within 7 days)"
                Write-Host "This appears to be an active installation. Performing update instead of full installation."
                $isUpdate = $true
            } else {
                Write-Host "No recent activity found in logs. Performing full installation."
            }
        } catch {
            Write-Host "Error checking log files: $_"
            Write-Host "Continuing with full installation."
        }
    } else {
        Write-Host "No log folder found. Performing full installation."
    }
} else {
    Write-Host "Installation directory does not exist. Performing full installation."
}

# If this is an update in offline mode and we have an installer jar, copy it to the temp directory
if ($isUpdate -and $offline_mode -and $has_installer_jar) {
    $installerTempDir = Join-Path $install_dir "installer\temp"
    
    # Create the temp directory if it doesn't exist
    if (-not (Test-Path $installerTempDir)) {
        Write-Host "Creating installer temp directory: $installerTempDir"
        New-Item -ItemType Directory -Path $installerTempDir -Force | Out-Null
    }
    
    # Copy the installer jar to the temp directory
    $installerJarDest = Join-Path $installerTempDir "installer.jar"
    Write-Host "Copying installer JAR for offline update: $installer_jar -> $installerJarDest"
    try {
        Copy-Item -Path $installer_jar -Destination $installerJarDest -Force
        Write-Host "Successfully copied installer JAR for offline update"
    } catch {
        Write-Host "Warning: Failed to copy installer JAR for offline update: $_"
    }
}


# Get hostname
$hs = $env:COMPUTERNAME
if ([string]::IsNullOrEmpty($hs)) {
    Write-Host "Warning: Could not read hostname. Falling back to manual input."
} else {
    Write-Host "-------------------"
    Write-Host "Hostname  : $hs"
    Write-Host "==================="
}

# Using manual input (both hostname and file detection are disabled)
$hostnameDetected = $false

# Prompt for Store Number and Workstation ID
Write-Host "Manual input mode (automatic detection is disabled)."
# Prompt for Store Number
Write-Host "Please enter the Store Number in one of these formats (or any custom format):"
Write-Host "  - 4 digits (e.g., 1234)"
Write-Host "  - 1 letter + 3 digits (e.g., R005)"
Write-Host "  - 2 letters + 2 digits (e.g., CA45)"
Write-Host "  - Custom format (e.g., STORE-105)"
$storeNumber = Read-Host "Store Number"
# Validate that something was entered
if ([string]::IsNullOrWhiteSpace($storeNumber)) {
    Write-Host "Store Number cannot be empty. Please try again."
    $storeNumber = Read-Host "Store Number"
}
# Prompt for Workstation ID
while ($true) {
    $workstationId = Read-Host "Please enter the Workstation ID (numeric)"
    if ($workstationId -match '^\d+$') {
        break
    }
    Write-Host "Invalid input. Please enter a numeric Workstation ID."
}

# Print final results
Write-Host "-------------------"
Write-Host "StoreNr   : $storeNumber"
Write-Host "WorkstationId: $workstationId"
Write-Host "-------------------"

# After the basic configuration section, update the onboarding call
Write-Host "Starting onboarding process for $ComponentType"

# Skip onboarding and store initialization if this is an update
if (-not $isUpdate) {
    # Call the onboarding script with the appropriate component type
    try {
        .\onboarding.ps1 -ComponentType $ComponentType -base_url $base_url
        Write-Host "$ComponentType onboarding completed successfully"

        # Execute store initialization right after successful onboarding
        # Skip store initialization for WDM
        if ($ComponentType -ne 'WDM') {
            Write-Host "Starting store initialization..."
            $storeInitScript = Join-Path $PSScriptRoot "store-initialization.ps1"
            if (Test-Path $storeInitScript) {
                try {
                    # Update get_store.json with the store ID
                    $getStoreJsonPath = Join-Path $PSScriptRoot "helper\init\get_store.json"
                    if (Test-Path $getStoreJsonPath) {
                        Write-Host "Creating processed copy of get_store.json with Store ID: $storeNumber"
                        # Create directory if it doesn't exist
                        $initPath = Join-Path $PSScriptRoot "helper\init"
                        if (-Not (Test-Path $initPath)) {
                            New-Item -ItemType Directory -Path $initPath -Force | Out-Null
                        }
                        # Create processed copy
                        $processedGetStorePath = Join-Path $initPath "get_store_processed.json"
                        # Read the original file
                        $getStoreJson = Get-Content -Path $getStoreJsonPath -Raw
                        # Replace the placeholder in memory
                        $processedGetStoreJson = $getStoreJson -replace '@RETAIL_STORE_ID@', $storeNumber
                        # Save to the processed file
                        Set-Content -Path $processedGetStorePath -Value $processedGetStoreJson
                        Write-Host "get_store_processed.json created successfully"
                    } else {
                        Write-Host "Warning: get_store.json not found at: $getStoreJsonPath"
                    }
                    
                    # Pass the values collected from hostname or user input
                    & $storeInitScript -ComponentType $ComponentType -base_url $base_url -StoreId $storeNumber -WorkstationId $workstationId
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "Store initialization completed successfully"
                    } else {
                        Write-Host "Warning: Store initialization failed with exit code $LASTEXITCODE"
                        exit 1
                    }
                }
                catch {
                    Write-Host "Error during store initialization: $_"
                    exit 1
                }
            } else {
                Write-Host "Error: Store initialization script not found at: $storeInitScript"
                exit 1
            }
        } else {
            Write-Host "Skipping store initialization for WDM component"
        }
    }
    catch {
        Write-Host "Error during $ComponentType onboarding: $_"
        exit 1
    }
} else {
    Write-Host "Skipping onboarding and store initialization for update"
}

# Read onboarding token
$onboardingToken = ""
if (-not $isUpdate) {
    $onboardingTokenPath = "onboarding.token"
    if (-not (Test-Path $onboardingTokenPath)) {
        Write-Host "Error: Onboarding token file not found at: $onboardingTokenPath"
        exit 1
    }
    $onboardingToken = Get-Content -Path $onboardingTokenPath -Raw
    $onboardingToken = $onboardingToken.Trim()
} else {
    Write-Host "Skipping onboarding token check for update mode"
    $onboardingToken = "not-required-for-update"
}

# Create configuration files
$installationToken = @"
configService.url=https://@Server@/config-service
cims.url=https://@Server@/cims
station.tenantId=001
station.storeId=@StoreNr@
station.workstationId=@WorkstationId@
station.applicationVersion=@Version@
station.systemType=$systemType
onboarding.token=$onboardingToken
dsg.url=https://@DsgServer@/dsg/content/cep/SoftwarePackage
"@

$installationToken = $installationToken.Replace("@StoreNr@", $storeNumber)
$installationToken = $installationToken.Replace("@WorkstationId@", $workstationId)
$installationToken = $installationToken.Replace("@Version@", $component_version)
$installationToken = $installationToken.Replace("@Server@", $server)
$installationToken = $installationToken.Replace("@DsgServer@", $dsg_server)

Set-Content -Path "installationtoken.txt" -Value $installationToken

# Create base64 token
$bytes = [System.Text.Encoding]::UTF8.GetBytes($installationToken)
$base64Token = [Convert]::ToBase64String($bytes)
Set-Content -Path "installationtoken.base64" -Value $base64Token

# Create addonpack.properties
$addonpackProps = @"
dsg.addonpack.url=https://$dsg_server/dsg/content/cep/AddOnPacks
addonpacks=
"@
Set-Content -Path "$install_dir\addonpack.properties" -Value $addonpackProps

# Only handle .p12 certificates for non-POS installations
if ($ComponentType -ne 'POS') {
    # Handle .p12 file if it exists
    $p12Files = Get-ChildItem -Path "." -Filter "*.p12"

    # Create security directory if it doesn't exist
    if (-not (Test-Path $security_dir)) {
        Write-Host "Creating security directory: $security_dir"
        New-Item -ItemType Directory -Path $security_dir -Force | Out-Null
    }

    # Check for certificates in the security directory
    $securityP12Files = Get-ChildItem -Path $security_dir -Filter "*.p12" -ErrorAction SilentlyContinue
    $ssl_path = $null

    # Check for certificates in the current directory
    $usedExistingCert = $false
}
if ($p12Files.Count -gt 0) {
    Write-Host "Found .p12 file(s) in script directory"
    
    # Check if we have certificates in security directory
    if ($securityP12Files.Count -gt 0) {
        Write-Host "Found existing certificate(s) in security directory, checking for name matches..."
        
        # Get certificate names from security directory
        $securityCertNames = $securityP12Files | ForEach-Object { $_.Name }
        
        # Check if any of our current certificates match by name
        $matchingCert = $p12Files | Where-Object { $securityCertNames -contains $_.Name } | Select-Object -First 1
        
        if ($matchingCert) {
            # Use the matching certificate from security directory
            $ssl_path = ($securityP12Files | Where-Object { $_.Name -eq $matchingCert.Name } | Select-Object -First 1).FullName
            Write-Host "Using existing certificate with matching name: $($matchingCert.Name) from security directory"
            $usedExistingCert = $true
        } else {
            # No matching certificate found, copy and use the new one
            Write-Host "Certificate in current directory has different name than existing ones, copying and using new certificate"
            
            # Copy the first p12 file found if there are multiple
            $newCert = $p12Files[0]
            $destPath = Join-Path $security_dir $newCert.Name
            Write-Host "Copying $($newCert.Name) to $destPath"
            Copy-Item -Path $newCert.FullName -Destination $destPath -Force
            
            # Use the newly copied certificate
            $ssl_path = $destPath
        }
    } else {
        # No certificates in security directory, copy all from current directory
        Write-Host "No certificates in security directory, copying all from current directory"
        
        # Copy each .p12 file found
        foreach ($p12File in $p12Files) {
            # Copy with original filename
            $destPath = Join-Path $security_dir $p12File.Name
            Write-Host "Copying $($p12File.Name) to $destPath"
            Copy-Item -Path $p12File.FullName -Destination $destPath -Force
            
            # Set the ssl_path to the first certificate copied
            if ($null -eq $ssl_path) {
                $ssl_path = $destPath
            }
        }
    }
} elseif ($securityP12Files.Count -gt 0) {
    # No certificates in current directory but some in security directory
    # Use the first .p12 file found in the security directory
    $ssl_path = $securityP12Files[0].FullName
    Write-Host "Found certificate at: $ssl_path"
    $usedExistingCert = $true
} else {
    # No certificate found anywhere
    Write-Host "Warning: No certificate found for Tomcat. The installation may fail if a certificate is required."
}

# Paths
$launchersPath = Join-Path $PSScriptRoot "helper\launchers"

# Verify launchers path exists
if (-Not (Test-Path $launchersPath)) {
    Write-Host "Launchers path does not exist: $launchersPath"
    exit
}

# Select the appropriate template file
$templateFile = if ($ComponentType -eq 'POS') { 
    Join-Path $launchersPath "launcher.pos.template" 
} elseif ($ComponentType -eq 'WDM') {
    Join-Path $launchersPath "launcher.wdm.template"
} elseif ($ComponentType -eq 'FLOW-SERVICE') {
    Join-Path $launchersPath "launcher.flow-service.template"
} elseif ($ComponentType -eq 'LPA-SERVICE') {
    Join-Path $launchersPath "launcher.lpa-service.template"
} elseif ($ComponentType -eq 'STOREHUB-SERVICE') {
    Join-Path $launchersPath "launcher.storehub-service.template"
} else { 
    Join-Path $launchersPath "launcher.wdm.template" 
}

if (-not (Test-Path $templateFile)) {
    Write-Host "Error: Template file $templateFile not found"
    exit 1
}

# Read the template content
$launcherProps = Get-Content -Path $templateFile -Raw

# Replace placeholders with actual values
$replacements = @{
    '@INSTALL_DIR@' = $install_dir
    '@BASE64_TOKEN@' = $base64Token
    '@OFFLINE_MODE@' = $(if ($offline_mode) { "1" } else { "0" })
    '@JRE_VERSION@' = $(if ($offline_mode -and -not [string]::IsNullOrEmpty($jre_version)) { $jre_version } else { "" })
    '@JRE_PACKAGE@' = $(if ($offline_mode -and $jre_files.Count -gt 0) { $jre_files[0].FullName } else { "" })
    '@INSTALLER_PACKAGE@' = $(if ($offline_mode -and $has_installer_jar) { $installer_jar } else { "" })
    '@SSL_PATH@' = $ssl_path
    '@SSL_PASSWORD@' = $ssl_password
    'C:\Program Files\Firebird\Firebird_3_0' = $firebird_server_path
    '@FIREBIRD_DRIVER_PATH_LOCAL@' = $firebird_driver_path_local
}

# Add Tomcat replacements if Tomcat files were found
if ($tomcat_files.Count -gt 0) {
    $replacements['@TOMCAT_VERSION@'] = $(if ($offline_mode) { $tomcat_version } else { "" })
    $replacements['@TOMCAT_PACKAGE@'] = $(if ($offline_mode) { $tomcat_files[0].FullName } else { "" })
}

# Add Jaybird driver path if found
if ($has_jaybird) {
    $replacements['@FIREBIRD_DRIVER_PATH_LOCAL@'] = $firebird_driver_path_local
}

# Apply all replacements
foreach ($key in $replacements.Keys) {
    $launcherProps = $launcherProps.Replace($key, $replacements[$key])
}

Write-Host "Writing launcher properties to file..."
Set-Content -Path "launcher.properties" -Value $launcherProps -Force
Write-Host "Launcher properties file created successfully. Launcher will use this for configuration."

# Download or use local Launcher
if (-not $offline_mode) {
    $download_url = "https://$base_url/dsg/content/cep/SoftwarePackage/$systemType/$component_version/Launcher.exe"
    Write-Host "Attempting to download Launcher.exe from: $download_url"
    try {
        # Try to use curl first (faster), fall back to WebClient if not available or fails
        if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
            Write-Host "Using curl for download..."
            try {
                curl.exe -L --progress-bar -o "Launcher.exe" "$download_url"
                if (-not (Test-Path "Launcher.exe") -or (Get-Item "Launcher.exe").Length -eq 0) {
                    throw "Curl download failed or produced empty file."
                }
                Write-Host "Successfully downloaded Launcher.exe using curl"
            } catch {
                Write-Host "Curl failed: $_. Falling back to WebClient..."
                $webClient = New-Object System.Net.WebClient
                $webClient.DownloadFile($download_url, "Launcher.exe")
            }
        } else {
            Write-Host "curl not available, using WebClient..."
            $webClient = New-Object System.Net.WebClient
            $webClient.DownloadFile($download_url, "Launcher.exe")
        }
        Write-Host "Successfully downloaded Launcher.exe"
    }
    catch {
        Write-Host "Error downloading Launcher.exe: $_"
        exit 1
    }
} else {
    # In offline mode, copy the Launcher.exe from the package directory to the current directory
    Write-Host "Copying Launcher.exe from $package_dir to current directory..."
    try {
        Copy-Item -Path $launcher_path -Destination ".\Launcher.exe" -Force
        Write-Host "Successfully copied Launcher.exe"
    }
    catch {
        Write-Host "Error copying Launcher.exe: $_"
        exit 1
    }
}

# Start the installation
Write-Host "Starting installation..."

# Check if installer log already exists and delete it
$installerLogPath = Join-Path $install_dir "installer\log\installer.log"
if (Test-Path $installerLogPath) {
    Write-Host "Found existing installer log file. Deleting to ensure clean installation..."
    try {
        Remove-Item -Path $installerLogPath -Force
        Write-Host "Existing installer log file deleted successfully."
    } catch {
        Write-Host "Warning: Failed to delete existing installer log file: $_"
        Write-Host "This might lead to confusing log output during installation."
    }
}

# Start Launcher with appropriate arguments for new installation or update
if ($isUpdate) {
    Write-Host "================================================================="
    Write-Host "                     RUNNING IN UPDATE MODE                      " -ForegroundColor Cyan
    Write-Host "================================================================="
    $launchArgs = @(
        "--mode", "unattended",
        "--forceDownload", "false",
        "--station.applicationVersion", $component_version,
        "--station.propertiesPath", $install_dir
    )
    Write-Host "Running Launcher with update arguments: $($launchArgs -join ' ')"
    $launcherProcess = Start-Process -FilePath ".\Launcher.exe" -ArgumentList $launchArgs -PassThru
} else {
    Write-Host "================================================================="
    Write-Host "                 RUNNING IN FULL INSTALLATION MODE               " -ForegroundColor Green
    Write-Host "================================================================="
    $launcherProcess = Start-Process -FilePath ".\Launcher.exe" -ArgumentList "--defaultsFile", "launcher.properties", "--mode", "unattended" -PassThru
}

# Check installation logs
$maxWaitTime = 7200 # 2 hours timeout
$maxLogWaitTime = 3600 # 1 hour timeout for download installers from DSG
$elapsed = 0
$logWaitElapsed = 0
$checkInterval = 2 # Check every 2 seconds
$lastLineNumber = 0
$firstLog = $true

Write-Host "Waiting for installation to complete..."
Write-Host "Monitoring log: $installerLogPath"

while ($elapsed -lt $maxWaitTime) {
    # Check if launcher is still running
    if ($launcherProcess.HasExited) {
        Write-Host "Launcher process has exited with code: $($launcherProcess.ExitCode)"
        Write-Host "Continuing to monitor logs for 5 seconds..."
        
        $postExitTime = 5
        while ($postExitTime -gt 0) {
            if (Test-Path $installerLogPath) {
                try {
                    # Read new lines from the log
                    $currentContent = Get-Content $installerLogPath -ErrorAction Stop
                    
                    if ($currentContent.Count -gt $lastLineNumber) {
                        $newLines = $currentContent[$lastLineNumber..($currentContent.Count-1)]
                        foreach ($line in $newLines) {
                            Write-Host "LOG: $line"
                        }
                        $lastLineNumber = $currentContent.Count
                    }
                }
                catch {
                    Write-Host "Error reading log file: $_"
                }
            }
            
            Write-Host -NoNewline "`rTime remaining for log monitoring: $postExitTime seconds..."
            Start-Sleep -Seconds 1
            $postExitTime--
        }
        Write-Host "`nCompleting installation..."
        
        # Final log check
        if (Test-Path $installerLogPath) {
            try {
                $finalLogContent = Get-Content $installerLogPath -ErrorAction Stop | Select-Object -Last 20
                if ($finalLogContent -match "Installation finished successfully") {
                    Write-Host "Installation completed successfully!"
                    Write-Host "Installation directory: $install_dir"
                    
                    # Component-specific completion messages
                    if ($ComponentType -eq 'WDM') {
                        Write-Host "WDM installation completed. Please check the following:"
                        Write-Host "1. Tomcat service status"
                        Write-Host "2. WDM application accessibility at https://localhost:8543"
                    } else {
                        Write-Host "$ComponentType installation completed. Please check the application status."
                    }
                    
                    # Cleanup: Move generated files to a results directory
                    $resultsDir = "results_$ComponentType"
                    Write-Host "Performing cleanup - Moving generated files to $resultsDir directory..."
                    
                    # Create the results directory if it doesn't exist
                    if (-not (Test-Path $resultsDir)) {
                        New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
                    }
                    
                    # Multiple attempts to ensure transcript is stopped
                    Write-Host "Making multiple attempts to stop the transcript before cleanup..."
                    try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                    Start-Sleep -Seconds 1
                    try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                    Start-Sleep -Seconds 1
                    try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                    Start-Sleep -Seconds 2
                    
                    # List of files to move
                    $filesToMove = @(
                        "installationtoken.txt",
                        "installationtoken.base64",
                        "launcher.properties",
                        "onboarding.token",
                        "Launcher.exe"
                    )
                    
                    # Add additional files specific to the installation - but only if they exist
                    $additionalFiles = Get-ChildItem -Path "." -Filter "*.log" -File -ErrorAction SilentlyContinue
                    if ($additionalFiles) {
                        foreach ($logFile in $additionalFiles) {
                            $filesToMove += $logFile.FullName
                        }
                    }
                    
                    # Find all JSON files in the current directory and helper subdirectories
                    $jsonFiles = @()
                    # Only include JSON files in the current directory, not in helper
                    $jsonFiles += Get-ChildItem -Path "." -Filter "*.json" -File -Depth 0 -ErrorAction SilentlyContinue
                    
                    if ($jsonFiles.Count -gt 0) {
                        Write-Host "Found $($jsonFiles.Count) JSON files to move"
                        foreach ($jsonFile in $jsonFiles) {
                            $filesToMove += $jsonFile.FullName
                        }
                    } else {
                        Write-Host "No JSON files need to be cleaned up"
                    }

                    # Move each file to the results directory
                    foreach ($file in $filesToMove) {
                        if (Test-Path $file) {
                            # Skip any files in helper directory
                            if ($file -like "*\helper\*") {
                                continue
                            }
                            
                            # Process only files in current directory
                            $destFile = Join-Path $resultsDir (Split-Path -Leaf $file)
                            
                            try {
                                # Copy first, then remove to ensure successful copy
                                Copy-Item -Path $file -Destination $destFile -Force
                                Write-Host "Moved: $file to $destFile"
                                Remove-Item -Path $file -Force
                            } catch {
                                Write-Host "Warning: Could not process $file to results directory: $_"
                            }
                        }
                    }
                    
                    # Final attempt to stop transcript and handle log file as last step
                    Write-Host "Performing final transcript stop and log file cleanup..."
                    try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                    Start-Sleep -Seconds 1
                    try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                    Start-Sleep -Seconds 1
                    try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                    Start-Sleep -Seconds 2
                    
                    # Move log file to results directory if it exists
                    if (Test-Path $logFile) {
                        $destLogFile = Join-Path $resultsDir $logFile
                        try {
                            Start-Sleep -Seconds 3  # Longer pause to ensure file handle is fully released
                            Write-Host "Copying log file: $logFile to $destLogFile"
                            Copy-Item -Path $logFile -Destination $destLogFile -Force
                            Write-Host "Console output log copied to: $destLogFile"
                            
                            # Try to remove original but don't fail if it can't be deleted
                            try {
                                Write-Host "Attempting to remove original log file..."
                                Remove-Item -Path $logFile -Force -ErrorAction SilentlyContinue
                                Write-Host "Original log file removed successfully."
                            } catch {
                                Write-Host "Note: Original log file will be cleaned up when PowerShell session ends."
                            }
                        } catch {
                            Write-Host "Warning: Could not copy log file to results directory: $_"
                        }
                    }
                    
                    Write-Host "Cleanup completed. Installation files have been moved to $resultsDir directory."
                    
                    # Final cleanup operations before exiting
                    Write-Host "Executing final cleanup before exit..."
                    [System.GC]::Collect()  # Force garbage collection
                    Start-Sleep -Seconds 1  # Give GC time to work
                    
                    exit 0
                }
                elseif ($finalLogContent -match "Installation failed") {
                    Write-Host "Installation failed. Please check the logs at: $installerLogPath"
                    exit 1
                }
            }
            catch {
                Write-Host "Error reading final log state: $_"
            }
        }
        
        # If we couldn't determine status from logs, use process exit code
        if ($launcherProcess.ExitCode -eq 0) {
            Write-Host "Launcher completed successfully based on exit code."
            Write-Host "Installation directory: $install_dir"
            
            # Cleanup: Move generated files to a results directory
            $resultsDir = "results_$ComponentType"
            Write-Host "Performing cleanup - Moving generated files to $resultsDir directory..."
            
            # Create the results directory if it doesn't exist
            if (-not (Test-Path $resultsDir)) {
                New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
            }
            
            # Multiple attempts to ensure transcript is stopped
            Write-Host "Making multiple attempts to stop the transcript before cleanup..."
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 1
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 1
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 2
            
            # List of files to move
            $filesToMove = @(
                "installationtoken.txt",
                "installationtoken.base64",
                "launcher.properties",
                "onboarding.token",
                "Launcher.exe"
            )
            
            # Add additional files specific to the installation - but only if they exist
            $additionalFiles = Get-ChildItem -Path "." -Filter "*.log" -File -ErrorAction SilentlyContinue
            if ($additionalFiles) {
                foreach ($logFile in $additionalFiles) {
                    $filesToMove += $logFile.FullName
                }
            }
            
            # Find all JSON files in the current directory and helper subdirectories
            $jsonFiles = @()
            # Only include JSON files in the current directory, not in helper
            $jsonFiles += Get-ChildItem -Path "." -Filter "*.json" -File -Depth 0 -ErrorAction SilentlyContinue
            
            if ($jsonFiles.Count -gt 0) {
                Write-Host "Found $($jsonFiles.Count) JSON files to move"
                foreach ($jsonFile in $jsonFiles) {
                    $filesToMove += $jsonFile.FullName
                }
            } else {
                Write-Host "No JSON files need to be cleaned up"
            }

            # Move each file to the results directory
            foreach ($file in $filesToMove) {
                if (Test-Path $file) {
                    # Skip any files in helper directory
                    if ($file -like "*\helper\*") {
                        continue
                    }
                    
                    # Process only files in current directory
                    $destFile = Join-Path $resultsDir (Split-Path -Leaf $file)
                    
                    try {
                        # Copy first, then remove to ensure successful copy
                        Copy-Item -Path $file -Destination $destFile -Force
                        Write-Host "Moved: $file to $destFile"
                        Remove-Item -Path $file -Force
                    } catch {
                        Write-Host "Warning: Could not process $file to results directory: $_"
                    }
                }
            }
            
            # Final attempt to stop transcript and handle log file as last step
            Write-Host "Performing final transcript stop and log file cleanup..."
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 1
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 1
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 2
            
            # Move log file to results directory if it exists
            if (Test-Path $logFile) {
                $destLogFile = Join-Path $resultsDir $logFile
                try {
                    Start-Sleep -Seconds 3  # Longer pause to ensure file handle is fully released
                    Write-Host "Copying log file: $logFile to $destLogFile"
                    Copy-Item -Path $logFile -Destination $destLogFile -Force
                    Write-Host "Console output log copied to: $destLogFile"
                    
                    # Try to remove original but don't fail if it can't be deleted
                    try {
                        Write-Host "Attempting to remove original log file..."
                        Remove-Item -Path $logFile -Force -ErrorAction SilentlyContinue
                        Write-Host "Original log file removed successfully."
                    } catch {
                        Write-Host "Note: Original log file will be cleaned up when PowerShell session ends."
                    }
                } catch {
                    Write-Host "Warning: Could not copy log file to results directory: $_"
                }
            }
            
            exit 0
        } else {
            Write-Host "Launcher failed with exit code: $($launcherProcess.ExitCode)"
            Write-Host "Please check the logs at: $installerLogPath"
            
            # Cleanup for failed installation - move files to errors directory
            $errorsDir = "errors_$ComponentType"
            Write-Host "Performing cleanup for failed installation - Moving files to $errorsDir directory..."
            
            # Create the errors directory if it doesn't exist
            if (-not (Test-Path $errorsDir)) {
                New-Item -ItemType Directory -Path $errorsDir -Force | Out-Null
            }
            
            # Multiple attempts to ensure transcript is stopped
            Write-Host "Making multiple attempts to stop the transcript before cleanup..."
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 1
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 1
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 2
            
            # List of files to move
            $filesToMove = @(
                "installationtoken.txt",
                "installationtoken.base64",
                "launcher.properties",
                "onboarding.token",
                "Launcher.exe"
            )
            
            # Add additional files specific to the installation - but only if they exist
            $additionalFiles = Get-ChildItem -Path "." -Filter "*.log" -File -ErrorAction SilentlyContinue
            if ($additionalFiles) {
                foreach ($logFile in $additionalFiles) {
                    $filesToMove += $logFile.FullName
                }
            }
            
            # Find all JSON files in the current directory and helper subdirectories
            $jsonFiles = @()
            # Only include JSON files in the current directory, not in helper
            $jsonFiles += Get-ChildItem -Path "." -Filter "*.json" -File -Depth 0 -ErrorAction SilentlyContinue
            
            if ($jsonFiles.Count -gt 0) {
                Write-Host "Found $($jsonFiles.Count) JSON files to move"
                foreach ($jsonFile in $jsonFiles) {
                    $filesToMove += $jsonFile.FullName
                }
            } else {
                Write-Host "No JSON files need to be cleaned up"
            }

            # Move each file to the errors directory
            foreach ($file in $filesToMove) {
                if (Test-Path $file) {
                    # Skip any files in helper directory
                    if ($file -like "*\helper\*") {
                        continue
                    }
                    
                    # Process only files in current directory
                    $destFile = Join-Path $errorsDir (Split-Path -Leaf $file)
                    
                    try {
                        # Copy first, then remove to ensure successful copy
                        Copy-Item -Path $file -Destination $destFile -Force
                        Write-Host "Moved: $file to $destFile"
                        Remove-Item -Path $file -Force
                    } catch {
                        Write-Host "Warning: Could not process $file to errors directory: $_"
                    }
                }
            }
            
            # Final attempt to stop transcript and handle log file as last step
            Write-Host "Performing final transcript stop and log file cleanup..."
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 1
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 1
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 2
            
            # Move log file to errors directory if it exists
            if (Test-Path $logFile) {
                $destLogFile = Join-Path $errorsDir $logFile
                try {
                    Start-Sleep -Seconds 3  # Longer pause to ensure file handle is fully released
                    Write-Host "Copying log file: $logFile to $destLogFile"
                    Copy-Item -Path $logFile -Destination $destLogFile -Force
                    Write-Host "Console output log copied to: $destLogFile"
                    
                    # Try to remove original but don't fail if it can't be deleted
                    try {
                        Write-Host "Attempting to remove original log file..."
                        Remove-Item -Path $logFile -Force -ErrorAction SilentlyContinue
                        Write-Host "Original log file removed successfully."
                    } catch {
                        Write-Host "Note: Original log file will be cleaned up when PowerShell session ends."
                    }
                } catch {
                    Write-Host "Warning: Could not copy log file to errors directory: $_"
                }
            }
            
            Write-Host "Cleanup completed. Failed installation files have been moved to $errorsDir directory."
            
            # Final attempt to stop transcript before exit
            Write-Host "Performing final transcript stop before exit..."
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 1
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 1
            try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 2
            
            exit 1
        }
    }

    if (Test-Path $installerLogPath) {
        try {
            # First time we see the log file
            if ($firstLog) {
                Write-Host "Log file created at: $installerLogPath"
                $firstLog = $false
            }

            # Read new lines from the log
            $currentContent = Get-Content $installerLogPath -ErrorAction Stop
            
            if ($currentContent.Count -gt $lastLineNumber) {
                $newLines = $currentContent[$lastLineNumber..($currentContent.Count-1)]
                foreach ($line in $newLines) {
                    Write-Host "LOG: $line"
                }
                $lastLineNumber = $currentContent.Count
            }

            # Check for completion
            $logContent = $currentContent | Select-Object -Last 20
            if ($logContent -match "Installation finished successfully") {
                Write-Host "Installation completed successfully!"
                Write-Host "Installation directory: $install_dir"
                
                # Component-specific completion messages
                if ($ComponentType -eq 'WDM') {
                    Write-Host "WDM installation completed. Please check the following:"
                    Write-Host "1. Tomcat service status"
                    Write-Host "2. WDM application accessibility at https://localhost:8543"
                } else {
                    Write-Host "$ComponentType installation completed. Please check the application status."
                }
                
                # Cleanup: Move generated files to a results directory
                $resultsDir = "results_$ComponentType"
                Write-Host "Performing cleanup - Moving generated files to $resultsDir directory..."
                
                # Create the results directory if it doesn't exist
                if (-not (Test-Path $resultsDir)) {
                    New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
                }
                
                # Multiple attempts to ensure transcript is stopped
                Write-Host "Making multiple attempts to stop the transcript before cleanup..."
                try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                Start-Sleep -Seconds 1
                try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                Start-Sleep -Seconds 1
                try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                Start-Sleep -Seconds 2
                
                # List of files to move
                $filesToMove = @(
                    "installationtoken.txt",
                    "installationtoken.base64",
                    "launcher.properties",
                    "onboarding.token",
                    "Launcher.exe"
                )
                
                # Add additional files specific to the installation - but only if they exist
                $additionalFiles = Get-ChildItem -Path "." -Filter "*.log" -File -ErrorAction SilentlyContinue
                if ($additionalFiles) {
                    foreach ($logFile in $additionalFiles) {
                        $filesToMove += $logFile.FullName
                    }
                }
                
                # Find all JSON files in the current directory and helper subdirectories
                $jsonFiles = @()
                # Only include JSON files in the current directory, not in helper
                $jsonFiles += Get-ChildItem -Path "." -Filter "*.json" -File -Depth 0 -ErrorAction SilentlyContinue
                
                if ($jsonFiles.Count -gt 0) {
                    Write-Host "Found $($jsonFiles.Count) JSON files to move"
                    foreach ($jsonFile in $jsonFiles) {
                        $filesToMove += $jsonFile.FullName
                    }
                } else {
                    Write-Host "No JSON files need to be cleaned up"
                }

                # Move each file to the results directory
                foreach ($file in $filesToMove) {
                    if (Test-Path $file) {
                        # Skip any files in helper directory
                        if ($file -like "*\helper\*") {
                            continue
                        }
                        
                        # Process only files in current directory
                        $destFile = Join-Path $resultsDir (Split-Path -Leaf $file)
                        
                        try {
                            # Copy first, then remove to ensure successful copy
                            Copy-Item -Path $file -Destination $destFile -Force
                            Write-Host "Moved: $file to $destFile"
                            Remove-Item -Path $file -Force
                        } catch {
                            Write-Host "Warning: Could not process $file to results directory: $_"
                        }
                    }
                }
                
                # Final attempt to stop transcript and handle log file as last step
                Write-Host "Performing final transcript stop and log file cleanup..."
                try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                Start-Sleep -Seconds 1
                try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                Start-Sleep -Seconds 1
                try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                Start-Sleep -Seconds 2
                
                # Move log file to results directory if it exists
                if (Test-Path $logFile) {
                    $destLogFile = Join-Path $resultsDir $logFile
                    try {
                        Start-Sleep -Seconds 3  # Longer pause to ensure file handle is fully released
                        Write-Host "Copying log file: $logFile to $destLogFile"
                        Copy-Item -Path $logFile -Destination $destLogFile -Force
                        Write-Host "Console output log copied to: $destLogFile"
                        
                        # Try to remove original but don't fail if it can't be deleted
                        try {
                            Write-Host "Attempting to remove original log file..."
                            Remove-Item -Path $logFile -Force -ErrorAction SilentlyContinue
                            Write-Host "Original log file removed successfully."
                        } catch {
                            Write-Host "Note: Original log file will be cleaned up when PowerShell session ends."
                        }
                    } catch {
                        Write-Host "Warning: Could not copy log file to results directory: $_"
                    }
                }
                
                Write-Host "Cleanup completed. Installation files have been moved to $resultsDir directory."
                
                # Final cleanup operations before exiting
                Write-Host "Executing final cleanup before exit..."
                [System.GC]::Collect()  # Force garbage collection
                Start-Sleep -Seconds 1  # Give GC time to work
                
                exit 0
            }
            elseif ($logContent -match "Installation failed") {
                Write-Host "Installation failed. Please check the logs at: $installerLogPath"
                
                # Cleanup for failed installation - move files to errors directory
                $errorsDir = "errors_$ComponentType"
                Write-Host "Performing cleanup for failed installation - Moving files to $errorsDir directory..."
                
                # Create the errors directory if it doesn't exist
                if (-not (Test-Path $errorsDir)) {
                    New-Item -ItemType Directory -Path $errorsDir -Force | Out-Null
                }
                
                # Multiple attempts to ensure transcript is stopped
                Write-Host "Making multiple attempts to stop the transcript before cleanup..."
                try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                Start-Sleep -Seconds 1
                try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                Start-Sleep -Seconds 1
                try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                Start-Sleep -Seconds 2
                
                # List of files to move
                $filesToMove = @(
                    "installationtoken.txt",
                    "installationtoken.base64",
                    "launcher.properties",
                    "onboarding.token",
                    "Launcher.exe"
                )
                
                # Add additional files specific to the installation - but only if they exist
                $additionalFiles = Get-ChildItem -Path "." -Filter "*.log" -File -ErrorAction SilentlyContinue
                if ($additionalFiles) {
                    foreach ($logFile in $additionalFiles) {
                        $filesToMove += $logFile.FullName
                    }
                }
                
                # Find all JSON files in the current directory and helper subdirectories
                $jsonFiles = @()
                # Only include JSON files in the current directory, not in helper
                $jsonFiles += Get-ChildItem -Path "." -Filter "*.json" -File -Depth 0 -ErrorAction SilentlyContinue
                
                if ($jsonFiles.Count -gt 0) {
                    Write-Host "Found $($jsonFiles.Count) JSON files to move"
                    foreach ($jsonFile in $jsonFiles) {
                        $filesToMove += $jsonFile.FullName
                    }
                } else {
                    Write-Host "No JSON files need to be cleaned up"
                }

                # Move each file to the errors directory
                foreach ($file in $filesToMove) {
                    if (Test-Path $file) {
                        # Skip any files in helper directory
                        if ($file -like "*\helper\*") {
                            continue
                        }
                        
                        # Process only files in current directory
                        $destFile = Join-Path $errorsDir (Split-Path -Leaf $file)
                        
                        try {
                            # Copy first, then remove to ensure successful copy
                            Copy-Item -Path $file -Destination $destFile -Force
                            Write-Host "Moved: $file to $destFile"
                            Remove-Item -Path $file -Force
                        } catch {
                            Write-Host "Warning: Could not process $file to errors directory: $_"
                        }
                    }
                }
                
                # Final attempt to stop transcript and handle log file as last step
                Write-Host "Performing final transcript stop and log file cleanup..."
                try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                Start-Sleep -Seconds 1
                try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                Start-Sleep -Seconds 1
                try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
                Start-Sleep -Seconds 2
                
                # Move log file to errors directory if it exists
                if (Test-Path $logFile) {
                    $destLogFile = Join-Path $errorsDir $logFile
                    try {
                        Start-Sleep -Seconds 3  # Longer pause to ensure file handle is fully released
                        Write-Host "Copying log file: $logFile to $destLogFile"
                        Copy-Item -Path $logFile -Destination $destLogFile -Force
                        Write-Host "Console output log copied to: $destLogFile"
                        
                        # Try to remove original but don't fail if it can't be deleted
                        try {
                            Write-Host "Attempting to remove original log file..."
                            Remove-Item -Path $logFile -Force -ErrorAction SilentlyContinue
                            Write-Host "Original log file removed successfully."
                        } catch {
                            Write-Host "Note: Original log file will be cleaned up when PowerShell session ends."
                        }
                    } catch {
                        Write-Host "Warning: Could not copy log file to errors directory: $_"
                    }
                }
                
                Write-Host "Cleanup completed. Failed installation files have been moved to $errorsDir directory."
                
                exit 1
            }
        }
        catch {
            Write-Host "Error reading log file: $_"
        }
    } else {
        $waitMessage = if (-not $offline.IsPresent) {
            "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed) - Downloading installation files from $base_url DSG"
        } else {
            "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed)"
        }
        Write-Host $waitMessage
        
        $logWaitElapsed += $checkInterval
        if ($logWaitElapsed -ge $maxLogWaitTime) {
            Write-Host "Error: Timeout waiting for installer log file to be created after $($maxLogWaitTime / 60) minutes"
            Write-Host "Expected log path: $installerLogPath"
            # Try to kill launcher process if it's still running
            if ($launcherProcess.HasExited -eq $false) {
                Write-Host "Terminating launcher process..."
                $launcherProcess.Kill()
            }
            exit 1
        }
    }
    
    Start-Sleep -Seconds $checkInterval
    $elapsed += $checkInterval
    
    # Show progress less frequently
    if ($elapsed % 30 -eq 0) {
        Write-Host "Installation in progress... ($(${elapsed}/60) minutes elapsed)"
    }
}

# Try to kill launcher process if it's still running after timeout
if (-not $launcherProcess.HasExited) {
    Write-Host "Terminating launcher process due to timeout..."
    $launcherProcess.Kill()
}

Write-Host "Warning: Installation timeout reached after 2 hours. Please check the installation logs at: $installerLogPath"
Write-Host "Installation directory: $install_dir"

# Cleanup for timeout failure
$errorsDir = "errors_$ComponentType"
Write-Host "Performing cleanup for timed out installation - Moving files to $errorsDir directory..."

# Create the errors directory if it doesn't exist
if (-not (Test-Path $errorsDir)) {
    New-Item -ItemType Directory -Path $errorsDir -Force | Out-Null
}

# Multiple attempts to ensure transcript is stopped
Write-Host "Making multiple attempts to stop the transcript before cleanup..."
try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
Start-Sleep -Seconds 1
try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
Start-Sleep -Seconds 1
try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
Start-Sleep -Seconds 2

# List of files to move
$filesToMove = @(
    "installationtoken.txt",
    "installationtoken.base64",
    "launcher.properties",
    "onboarding.token",
    "Launcher.exe"
)

# Add additional files specific to the installation - but only if they exist
$additionalFiles = Get-ChildItem -Path "." -Filter "*.log" -File -ErrorAction SilentlyContinue
if ($additionalFiles) {
    foreach ($logFile in $additionalFiles) {
        $filesToMove += $logFile.FullName
    }
}

# Find all JSON files in the current directory and helper subdirectories
$jsonFiles = @()
# Only include JSON files in the current directory, not in helper
$jsonFiles += Get-ChildItem -Path "." -Filter "*.json" -File -Depth 0 -ErrorAction SilentlyContinue

if ($jsonFiles.Count -gt 0) {
    Write-Host "Found $($jsonFiles.Count) JSON files to move"
    foreach ($jsonFile in $jsonFiles) {
        $filesToMove += $jsonFile.FullName
    }
} else {
    Write-Host "No JSON files need to be cleaned up"
}

# Move each file to the errors directory
foreach ($file in $filesToMove) {
    if (Test-Path $file) {
        # Skip any files in helper directory
        if ($file -like "*\helper\*") {
            continue
        }
        
        # Process only files in current directory
        $destFile = Join-Path $errorsDir (Split-Path -Leaf $file)
        
        try {
            # Copy first, then remove to ensure successful copy
            Copy-Item -Path $file -Destination $destFile -Force
            Write-Host "Moved: $file to $destFile"
            Remove-Item -Path $file -Force
        } catch {
            Write-Host "Warning: Could not process $file to errors directory: $_"
        }
    }
}

# Final attempt to stop transcript and handle log file as last step
Write-Host "Performing final transcript stop and log file cleanup..."
try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
Start-Sleep -Seconds 1
try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
Start-Sleep -Seconds 1
try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
Start-Sleep -Seconds 2

# Move log file to errors directory if it exists
if (Test-Path $logFile) {
    $destLogFile = Join-Path $errorsDir $logFile
    try {
        Start-Sleep -Seconds 3  # Longer pause to ensure file handle is fully released
        Write-Host "Copying log file: $logFile to $destLogFile"
        Copy-Item -Path $logFile -Destination $destLogFile -Force
        Write-Host "Console output log copied to: $destLogFile"
        
        # Try to remove original but don't fail if it can't be deleted
        try {
            Write-Host "Attempting to remove original log file..."
            Remove-Item -Path $logFile -Force -ErrorAction SilentlyContinue
            Write-Host "Original log file removed successfully."
        } catch {
            Write-Host "Note: Original log file will be cleaned up when PowerShell session ends."
        }
    } catch {
        Write-Host "Warning: Could not copy log file to errors directory: $_"
    }
}

Write-Host "Cleanup completed. Timed out installation files have been moved to $errorsDir directory."

exit 1 