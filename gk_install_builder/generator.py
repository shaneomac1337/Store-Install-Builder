import os
import re
import json
import shutil
import customtkinter as ctk
import base64
import platform
from webdav3.client import Client
from webdav3.exceptions import WebDavException
from datetime import datetime
from urllib.parse import unquote
import requests
import logging
from string import Template
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import time
import threading
import queue
from detection import DetectionManager

# Disable insecure request warnings
urllib3.disable_warnings(InsecureRequestWarning)

class WebDAVBrowser:
    def __init__(self, base_url, username=None, password=None):
        if not base_url.startswith('http'):
            base_url = f'https://{base_url}'
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.connected = False
        
        self.options = {
            'webdav_hostname': f"{self.base_url}/dsg/webdav",
            'webdav_login': username,
            'webdav_password': password,
            'disable_check': True,
            'verbose': True,
            'verify': False
        }
        
        print("\nWebDAV Client Options:")
        print(f"Hostname: {self.options['webdav_hostname']}")
        print(f"Username: {self.options['webdav_login']}")
        
        self.client = Client(self.options)
        self.current_path = "/"

    def _normalize_path(self, path):
        """Normalize WebDAV path"""
        # Simple path normalization without any special cases
        path = path.replace('\\', '/')
        path = path.strip('/')
        return '/' + path if path else '/'

    def list_directories(self, path="/"):
        """List files and directories in the current path"""
        try:
            # Check if connected
            if not self.connected:
                print("Warning: Not connected to WebDAV")
                return []
                
            # Normalize and store the path
            path = self._normalize_path(path)
            print(f"Listing directory: {path}")  # Debug print
            
            # Get directory listing
            files = self.client.list(path)
            items = []
            
            # Process each item
            for file_path in files:
                # Skip special directories
                if file_path in ['./', '../']:
                    continue
                
                # Clean up the name without any special handling
                name = os.path.basename(file_path.rstrip('/'))
                if not name:
                    continue
                
                # Simple directory check
                is_directory = file_path.endswith('/')
                
                # Add to results without any conditions
                items.append({
                    'name': name,
                    'is_directory': is_directory
                })
            
            return items
            
        except Exception as e:
            print(f"Error listing directory: {str(e)}")
            return []

    def connect(self):
        """Test WebDAV connection"""
        try:
            print("Testing WebDAV connection with:")
            print(f"URL: {self.options['webdav_hostname']}")
            print(f"Username: {self.username}")
            
            files = self.client.list()
            print(f"Connection successful. Found {len(files)} items")
            self.connected = True
            return True, "Connected successfully"
        except Exception as e:
            print(f"Connection failed: {str(e)}")
            self.connected = False
            return False, f"Connection failed: {str(e)}"

    def list_directory(self, path="/"):
        """Alias for list_directories"""
        return self.list_directories(path)

class ProjectGenerator:
    def __init__(self, parent_window=None):
        self.template_dir = "templates"
        self.helper_structure = {
            "launchers": [
                "launcher.pos.template",
                "launcher.wdm.template",
                "launcher.flow-service.template",
                "launcher.lpa-service.template",
                "launcher.storehub-service.template"
            ],
            "onboarding": [
                "pos.onboarding.json",
                "wdm.onboarding.json",
                "flow-service.onboarding.json",
                "lpa-service.onboarding.json",
                "storehub-service.onboarding.json"
            ],
            "tokens": [
                "basic_auth_password.txt",
                "form_password.txt"
            ],
            "init": [
                "get_store.json",
                {
                    "storehub": [
                        "update_config.json"
                    ]
                }
            ]
        }
        self.webdav_browser = None
        self.parent_window = parent_window  # Rename to parent_window for consistency
        self.detection_manager = DetectionManager()
        
        # Enable file detection by default
        self.detection_manager.enable_file_detection(True)

    def create_webdav_browser(self, base_url, username=None, password=None):
        """Create a new WebDAV browser instance"""
        self.webdav_browser = WebDAVBrowser(base_url, username, password)
        return self.webdav_browser

    def generate(self, config):
        """Generate project from configuration"""
        try:
            # Get absolute output directory path
            output_dir = os.path.abspath(config["output_dir"])
            print(f"Creating output directory: {output_dir}")
            
            # Create output directory and all parent directories if they don't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Store the original working directory
            original_cwd = os.getcwd()
            
            # Print debug information
            print(f"Current working directory: {original_cwd}")
            print(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")
            print(f"Output directory: {output_dir}")
            
            # Create project structure
            self._create_directory_structure(output_dir)
            
            # Copy certificate if it exists
            self._copy_certificate(output_dir, config)
            
            # Generate main scripts by modifying the original files
            self._generate_gk_install(output_dir, config)
            self._generate_onboarding(output_dir, config)
            
            # Copy and modify helper files
            self._copy_helper_files(output_dir, config)
            
            self._show_success(f"Project generated in: {output_dir}")
        except Exception as e:
            self._show_error(f"Failed to generate project: {str(e)}")
            # Print detailed error for debugging
            import traceback
            print(f"Error details: {traceback.format_exc()}")

    def _create_directory_structure(self, output_dir):
        """Create the project directory structure"""
        for dir_name in self.helper_structure.keys():
            os.makedirs(os.path.join(output_dir, "helper", dir_name), exist_ok=True)

    def _copy_certificate(self, output_dir, config):
        """Copy SSL certificate to output directory if it exists"""
        try:
            cert_path = config.get("certificate_path", "")
            if cert_path and os.path.exists(cert_path):
                # Copy certificate to output directory with the same name
                cert_filename = os.path.basename(cert_path)
                dest_path = os.path.join(output_dir, cert_filename)
                shutil.copy2(cert_path, dest_path)
                print(f"Copied certificate from {cert_path} to {dest_path}")
                
                return True
        except Exception as e:
            print(f"Warning: Failed to copy certificate: {str(e)}")
        
        return False

    def _generate_gk_install(self, output_dir, config):
        """Generate GKInstall script with replaced values based on platform"""
        try:
            # Get platform from config (default to Windows if not specified)
            platform = config.get("platform", "Windows")
            
            # Get hostname detection setting
            use_hostname_detection = config.get("use_hostname_detection", True)
            
            # Load detection configuration if available
            if "detection_config" in config:
                self.detection_manager.set_config(config["detection_config"])
            else:
                # If no detection_config is available but detection is enabled,
                # initialize with default settings based on platform and component type
                if self.detection_manager.is_detection_enabled():
                    # Create a default detection configuration
                    default_config = {
                        "file_detection_enabled": True,
                        "use_base_directory": True,
                        "base_directory": "C:\\gkretail\\stations" if platform == "Windows" else "/usr/local/gkretail/stations"
                    }
                    self.detection_manager.set_config(default_config)
                    
                    # Add this config back to main config to save for future use
                    config["detection_config"] = default_config
                    
                    print("Initializing detection with default settings:")
                    print(f"Base directory: {default_config['base_directory']}")
            
            # Set environment variable for Firebird server path
            firebird_server_path = config.get("firebird_server_path", "")
            if firebird_server_path:
                os.environ["FIREBIRD_SERVER_PATH"] = firebird_server_path
                print(f"Setting FIREBIRD_SERVER_PATH environment variable to: {firebird_server_path}")
            else:
                print("Warning: firebird_server_path is not set in config")
                
            # Set environment variable for Jaybird driver path
            firebird_driver_path_local = config.get("firebird_driver_path_local", "")
            if firebird_driver_path_local:
                os.environ["FIREBIRD_DRIVER_PATH_LOCAL"] = firebird_driver_path_local
                print(f"Setting FIREBIRD_DRIVER_PATH_LOCAL environment variable to: {firebird_driver_path_local}")
            else:
                # Set default paths based on platform
                if platform == "Windows":
                    default_path = "C:\\gkretail\\Jaybird"
                else:
                    default_path = "/usr/local/gkretail/Jaybird"
                os.environ["FIREBIRD_DRIVER_PATH_LOCAL"] = default_path
                print(f"Setting default FIREBIRD_DRIVER_PATH_LOCAL to: {default_path}")
            
            # Determine template and output paths based on platform
            if platform == "Windows":
                template_filename = "GKInstall.ps1.template"
                output_filename = "GKInstall.ps1"
            else:  # Linux
                template_filename = "GKInstall.sh.template"
                output_filename = "GKInstall.sh"
            
            # Use absolute paths for template and output
            template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", template_filename)
            output_path = os.path.join(output_dir, output_filename)
            
            print(f"Generating {output_filename}:")
            print(f"  Template path: {template_path}")
            print(f"  Output path: {output_path}")
            print(f"  Use hostname detection: {use_hostname_detection}")
            
            # Check if template exists
            if not os.path.exists(template_path):
                raise Exception(f"Template file not found: {template_path}")
            
            with open(template_path, 'r') as f:
                template = f.read()
                
            # Apply custom regex if available
            if "detection_config" in config and "hostname_detection" in config["detection_config"]:
                # Get the appropriate regex pattern based on platform
                regex_key = "windows_regex" if platform == "Windows" else "linux_regex"
                
                if regex_key in config["detection_config"]["hostname_detection"]:
                    custom_regex = config["detection_config"]["hostname_detection"][regex_key]
                    
                    # Debug info
                    print(f"Using custom hostname detection regex: {custom_regex}")
                    
                    # For Windows (PowerShell) - replace the regex in the hostname detection section
                    if platform == "Windows":
                        # Replace the hostname detection regex in PowerShell
                        template = self._replace_hostname_regex_powershell(template, custom_regex)
                    else:
                        # Replace the hostname detection regex in Bash
                        template = self._replace_hostname_regex_bash(template, custom_regex)
            
            # Get version information
            default_version = config.get("version", "v1.0.0")
            use_version_override = config.get("use_version_override", False)
            pos_version = config.get("pos_version", default_version)
            wdm_version = config.get("wdm_version", default_version)
            flow_service_version = config.get("flow_service_version", default_version)
            lpa_service_version = config.get("lpa_service_version", default_version)
            storehub_service_version = config.get("storehub_service_version", default_version)
            
            # Get system types from config
            pos_system_type = config.get("pos_system_type", "GKR-OPOS-CLOUD")
            wdm_system_type = config.get("wdm_system_type", "CSE-wdm")
            flow_service_system_type = config.get("flow_service_system_type", "GKR-FLOWSERVICE-CLOUD")
            lpa_service_system_type = config.get("lpa_service_system_type", "CSE-lps-lpa")
            storehub_service_system_type = config.get("storehub_service_system_type", "CSE-sh-cloud")
            
            print(f"Using system types from config:")
            print(f"  POS System Type: {pos_system_type}")
            print(f"  WDM System Type: {wdm_system_type}")
            print(f"  Flow Service System Type: {flow_service_system_type}")
            print(f"  LPA Service System Type: {lpa_service_system_type}")
            print(f"  StoreHub Service System Type: {storehub_service_system_type}")
            
            # Common replacements for both Windows and Linux
            replacements = []
            
            # Get the base URL and base install directory
            base_url = config.get("base_url", "test.cse.cloud4retail.co")
            base_install_dir = config.get("base_install_dir", "/usr/local/gkretail" if platform == "Linux" else "C:\\gkretail")
            
            # Get Firebird server path from config
            firebird_server_path = config.get("firebird_server_path", "")
            
            # Get tenant ID from config
            tenant_id = config.get("tenant_id", "001")
            
            if platform == "Windows":
                # Windows-specific replacements
                replacements = [
                    ("test.cse.cloud4retail.co", base_url),
                    ("C:\\\\gkretail", base_install_dir.replace("\\", "\\\\")),
                    ('"v1.0.0"', f'"{default_version}"'),
                    ("CSE-OPOS-CLOUD", pos_system_type),
                    ("CSE-wdm", wdm_system_type),
                    ("CSE-FLOWSERVICE-CLOUD", flow_service_system_type),
                    ("CSE-lps-lpa", lpa_service_system_type),
                    ("CSE-sh-cloud", storehub_service_system_type),
                    ("@POS_VERSION@", pos_version),
                    ("@WDM_VERSION@", wdm_version),
                    ("@FLOW_SERVICE_VERSION@", flow_service_version),
                    ("@LPA_SERVICE_VERSION@", lpa_service_version),
                    ("@STOREHUB_SERVICE_VERSION@", storehub_service_version),
                    ("@FIREBIRD_SERVER_PATH@", firebird_server_path),
                    ("station.tenantId=001", f"station.tenantId={tenant_id}")
                ]
                
                # Add version function for component-specific versions
                if use_version_override:
                    # We're no longer using the function approach, so we don't need to add the function
                    pass
                else:
                    # We're no longer using the function approach, so we don't need to add the function
                    pass
                
            else:  # Linux
                # Linux-specific replacements
                replacements = [
                    ("test.cse.cloud4retail.co", base_url),
                    ("/usr/local/gkretail", base_install_dir),
                    ('version="v1.0.0"', f'version="{default_version}"'),
                    ("CSE-OPOS-CLOUD", pos_system_type),
                    ("CSE-wdm", wdm_system_type),
                    ("CSE-FLOWSERVICE-CLOUD", flow_service_system_type),
                    ("CSE-lps-lpa", lpa_service_system_type),
                    ("CSE-sh-cloud", storehub_service_system_type),
                    ("@POS_VERSION@", pos_version),
                    ("@WDM_VERSION@", wdm_version),
                    ("@FLOW_SERVICE_VERSION@", flow_service_version),
                    ("@LPA_SERVICE_VERSION@", lpa_service_version),
                    ("@STOREHUB_SERVICE_VERSION@", storehub_service_version),
                    ("@FIREBIRD_SERVER_PATH@", firebird_server_path),
                    ("station.tenantId=001", f"station.tenantId={tenant_id}")
                ]
                
                # Add version function for component-specific versions (bash version)
                if use_version_override:
                    # We're no longer using the function approach, so we don't need to add the function
                    pass
                else:
                    # We're no longer using the function approach, so we don't need to add the function
                    pass
            
            # Update the download URL to use the component-specific version with fallback logic
            if platform == "Windows":
                download_url_line = '$download_url = "https://$base_url/dsg/content/cep/SoftwarePackage/$systemType/$version/Launcher.exe"'
                
                if use_version_override:
                    # Create the switch statement with direct values instead of using format
                    new_download_url_line = f'''# Set component version directly based on system type instead of calling the function
$component_version = switch ($systemType) {{
    "{pos_system_type}" {{ "{pos_version}" }}
    "{wdm_system_type}" {{ "{wdm_version}" }}
    "{flow_service_system_type}" {{ "{flow_service_version}" }}
    "{lpa_service_system_type}" {{ "{lpa_service_version}" }}
    "{storehub_service_system_type}" {{ "{storehub_service_version}" }}
    default {{ "" }}
}}

# If the component version is empty or null, fall back to the default version
if ([string]::IsNullOrEmpty($component_version)) {{
    $component_version = $version
}}
$download_url = "https://$base_url/dsg/content/cep/SoftwarePackage/$systemType/$component_version/Launcher.exe"'''
                else:
                    # If not using version override, all versions will be empty strings
                    new_download_url_line = f'''# Set component version directly based on system type instead of calling the function
$component_version = switch ($systemType) {{
    "{pos_system_type}" {{ "" }}
    "{wdm_system_type}" {{ "" }}
    "{flow_service_system_type}" {{ "" }}
    "{lpa_service_system_type}" {{ "" }}
    "{storehub_service_system_type}" {{ "" }}
    default {{ "" }}
}}

# If the component version is empty or null, fall back to the default version
if ([string]::IsNullOrEmpty($component_version)) {{
    $component_version = $version
}}
$download_url = "https://$base_url/dsg/content/cep/SoftwarePackage/$systemType/$component_version/Launcher.exe"'''
                
                template = template.replace(download_url_line, new_download_url_line)
            else:  # Linux
                download_url_line = 'download_url="https://$base_url/dsg/content/cep/SoftwarePackage/$systemType/$version/Launcher.run"'
                
                if use_version_override:
                    # Create the case statement with direct values instead of using format
                    new_download_url_line = f'''# Set component version directly based on system type
case "$systemType" in
    "{pos_system_type}")
        component_version="{pos_version}"
        ;;
    "{wdm_system_type}")
        component_version="{wdm_version}"
        ;;
    "{flow_service_system_type}")
        component_version="{flow_service_version}"
        ;;
    "{lpa_service_system_type}")
        component_version="{lpa_service_version}"
        ;;
    "{storehub_service_system_type}")
        component_version="{storehub_service_version}"
        ;;
    *)
        component_version=""
        ;;
esac

# If the component version is empty or null, fall back to the default version
if [ -z "$component_version" ]; then
    component_version="$version"
fi
download_url="https://$base_url/dsg/content/cep/SoftwarePackage/$systemType/$component_version/Launcher.run"'''
                else:
                    # If not using version override, all versions will be empty strings
                    new_download_url_line = f'''# Set component version directly based on system type
case "$systemType" in
    "{pos_system_type}")
        component_version=""
        ;;
    "{wdm_system_type}")
        component_version=""
        ;;
    "{flow_service_system_type}")
        component_version=""
        ;;
    "{lpa_service_system_type}")
        component_version=""
        ;;
    "{storehub_service_system_type}")
        component_version=""
        ;;
    *)
        component_version=""
        ;;
esac

# If the component version is empty or null, fall back to the default version
if [ -z "$component_version" ]; then
    component_version="$version"
fi
download_url="https://$base_url/dsg/content/cep/SoftwarePackage/$systemType/$component_version/Launcher.run"'''
                
                template = template.replace(download_url_line, new_download_url_line)
            
            # Apply all replacements
            for old, new in replacements:
                template = template.replace(old, new)
            
            # Create helper/launchers directory
            launchers_dir = os.path.join(output_dir, "helper", "launchers")
            os.makedirs(launchers_dir, exist_ok=True)
            
            # Generate launcher templates with custom settings
            self._generate_launcher_templates(launchers_dir, config)
            
            # Apply hostname detection setting
            if not use_hostname_detection:
                if platform == "Windows":
                    # Locate the hostname detection section for PowerShell
                    hostname_section_start = "# Get hostname"
                    hostname_section_end = "if (-not $hostnameDetected) {"
                    manual_input_end = "# Print final results"
                    
                    # Find positions in the template
                    start_pos = template.find(hostname_section_start)
                    conditional_pos = template.find(hostname_section_end, start_pos) if start_pos != -1 else -1
                    end_marker_pos = template.find(manual_input_end, conditional_pos) if conditional_pos != -1 else -1
                    
                    if start_pos != -1 and conditional_pos != -1 and end_marker_pos != -1:
                        # Replace the entire hostname detection section with direct manual input
                        manual_input_code = """# Manual input only (hostname detection disabled)
$storeNumber = ""
$workstationId = ""

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
while true; do
    $workstationId = Read-Host "Please enter the Workstation ID (numeric)"
    if [[ "$workstationId" =~ ^[0-9]+$ ]]; then
        break
    fi
    Write-Host "Invalid input. Please enter a numeric Workstation ID."
done

"""
                        # Replace the entire section
                        template = template[:start_pos] + manual_input_code + template[end_marker_pos:]
                        print("Replaced hostname detection code with manual input in PowerShell script")
                
                else:  # Linux
                    # Locate the hostname detection section for Bash
                    hostname_section_start = "# Get hostname"
                    hostname_section_end = "if [ \"$hostnameDetected\" = false ]; then"
                    manual_input_end = "# Print final results"
                    
                    # Find positions in the template
                    start_pos = template.find(hostname_section_start)
                    conditional_pos = template.find(hostname_section_end, start_pos) if start_pos != -1 else -1
                    end_marker_pos = template.find(manual_input_end, conditional_pos) if conditional_pos != -1 else -1
                    
                    if start_pos != -1 and conditional_pos != -1 and end_marker_pos != -1:
                        # Replace the entire hostname detection section with direct manual input
                        manual_input_code = """# Manual input only (hostname detection disabled)
storeNumber=""
workstationId=""

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

"""
                        # Replace the entire section
                        template = template[:start_pos] + manual_input_code + template[end_marker_pos:]
                        print("Replaced hostname detection code with manual input in Bash script")
            
            # Apply file detection settings if enabled
            if self.detection_manager.is_detection_enabled():
                if platform == "Windows":
                    # Instead of trying to determine component type from filename,
                    # use a placeholder that will be replaced with the actual ComponentType parameter
                    station_detection_code = '''
# File detection for the current component ($ComponentType)
$fileDetectionEnabled = $true
$componentType = $ComponentType

# Check if we're using base directory or custom paths
$useBaseDirectory = $"{is_using_base_dir}".ToLower()

if ($useBaseDirectory -eq "true") {{
    # Use base directory approach
    $basePath = "{base_dir}"
    $customFilenames = @{{
        "POS" = "{pos_filename}";
        "WDM" = "{wdm_filename}";
        "FLOW-SERVICE" = "{flow_filename}";
        "LPA-SERVICE" = "{lpa_filename}";
        "STOREHUB-SERVICE" = "{sh_filename}"
    }}

    # Get the appropriate station file for the current component
    $stationFileName = $customFilenames[$componentType]
    if (-not $stationFileName) {{
        $stationFileName = "$componentType.station"
    }}

    $stationFilePath = Join-Path $basePath $stationFileName
}} else {{
    # Use custom paths approach
    $customPaths = @{{
        "POS" = "{pos_path}";
        "WDM" = "{wdm_path}";
        "FLOW-SERVICE" = "{flow_path}";
        "LPA-SERVICE" = "{lpa_path}";
        "STOREHUB-SERVICE" = "{sh_path}"
    }}
    
    # Get the appropriate station file path for the current component
    $stationFilePath = $customPaths[$componentType]
    if (-not $stationFilePath) {{
        Write-Host "Warning: No custom path defined for $componentType" -ForegroundColor Yellow
        # Fallback to a default path
        $stationFilePath = "C:\gkretail\stations\$componentType.station"
    }}
}}

# Check if hostname detection failed and file detection is enabled
if (-not $hostnameDetected -and $fileDetectionEnabled) {{
    Write-Host "Trying file detection for $componentType using $stationFilePath"
    
    if (Test-Path $stationFilePath) {{
        $fileContent = Get-Content -Path $stationFilePath -Raw -ErrorAction SilentlyContinue
        
        if ($fileContent) {{
            $lines = $fileContent -split "`r?`n"
            
            foreach ($line in $lines) {{
                if ($line -match "StoreID=(.+)") {{
                    $storeNumber = $matches[1].Trim()
                    Write-Host "Found Store ID in file: $storeNumber"
                }}
                
                if ($line -match "WorkstationID=(.+)") {{
                    $workstationId = $matches[1].Trim()
                    Write-Host "Found Workstation ID in file: $workstationId"
                }}
            }}
            
            # Validate extracted values
            if ($storeNumber -and $workstationId -match '^\d+$') {{
                $script:hostnameDetected = $true  # Use $script: scope to ensure it affects the parent scope
                Write-Host "Successfully detected values from file:"
                Write-Host "Store Number: $storeNumber"
                Write-Host "Workstation ID: $workstationId"
            }}
        }}
    }} else {{
        Write-Host "Station file not found at: $stationFilePath"
    }}
}}
'''.format(
    is_using_base_dir=str(self.detection_manager.is_using_base_directory()).lower(),
    base_dir=self.detection_manager.get_base_directory().replace('\\', '\\\\'),
    pos_filename=self.detection_manager.get_custom_filename("POS"),
    wdm_filename=self.detection_manager.get_custom_filename("WDM"),
    flow_filename=self.detection_manager.get_custom_filename("FLOW-SERVICE"),
    lpa_filename=self.detection_manager.get_custom_filename("LPA-SERVICE"),
    sh_filename=self.detection_manager.get_custom_filename("STOREHUB-SERVICE"),
    pos_path=self.detection_manager.detection_config["detection_files"]["POS"].replace('\\', '\\\\'),
    wdm_path=self.detection_manager.detection_config["detection_files"]["WDM"].replace('\\', '\\\\'),
    flow_path=self.detection_manager.detection_config["detection_files"]["FLOW-SERVICE"].replace('\\', '\\\\'),
    lpa_path=self.detection_manager.detection_config["detection_files"]["LPA-SERVICE"].replace('\\', '\\\\'),
    sh_path=self.detection_manager.detection_config["detection_files"]["STOREHUB-SERVICE"].replace('\\', '\\\\')
)
                    
                    # Find where to insert the file detection code
                    if not use_hostname_detection:
                        # If hostname detection is disabled, we need to insert after the manual input code
                        insert_marker = "# Print final results"
                    else:
                        # In the updated template, we look for the placeholder for file detection code
                        insert_marker = "# File detection code will be inserted here by the generator"
                    
                    # Find the position to insert the code
                    insert_pos = template.find(insert_marker)
                    if insert_pos != -1:
                        # Insert the detection code at the appropriate position
                        template = template[:insert_pos] + station_detection_code + template[insert_pos + len(insert_marker):]
                        print(f"Added dynamic station detection code to PowerShell script")
                    else:
                        print(f"Warning: Could not find insertion point for station detection code in PowerShell script")
                
                else:  # Linux
                    # Similar approach for Linux/Bash script
                    station_detection_code = '''
# File detection for the current component ($COMPONENT_TYPE)
fileDetectionEnabled=true
componentType="$COMPONENT_TYPE"

# Check if we're using base directory or custom paths
useBaseDirectory="{is_using_base_dir}"

if [ "$useBaseDirectory" = "True" ]; then
    # Use base directory approach
    basePath="{base_dir}"
    declare -A customFilenames
    customFilenames["POS"]="{pos_filename}"
    customFilenames["WDM"]="{wdm_filename}"
    customFilenames["FLOW-SERVICE"]="{flow_filename}"
    customFilenames["LPA-SERVICE"]="{lpa_filename}"
    customFilenames["STOREHUB-SERVICE"]="{sh_filename}"

    # Get the appropriate station file for the current component
    stationFileName="${{customFilenames[$componentType]}}"
    if [ -z "$stationFileName" ]; then
        stationFileName="$componentType.station"
    fi

    stationFilePath="$basePath/$stationFileName"
else
    # Use custom paths approach
    declare -A customPaths
    customPaths["POS"]="{pos_path}"
    customPaths["WDM"]="{wdm_path}"
    customPaths["FLOW-SERVICE"]="{flow_path}"
    customPaths["LPA-SERVICE"]="{lpa_path}"
    customPaths["STOREHUB-SERVICE"]="{sh_path}"
    
    # Get the appropriate station file path for the current component
    stationFilePath="${{customPaths[$componentType]}}"
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
                storeNumber="${{BASH_REMATCH[1]}}"
                echo "Found Store ID in file: $storeNumber"
            fi
            
            if [[ "$line" =~ WorkstationID=(.+) ]]; then
                workstationId="${{BASH_REMATCH[1]}}"
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
'''.format(
    is_using_base_dir=str(self.detection_manager.is_using_base_directory()),
    base_dir=self.detection_manager.get_base_directory(),
    pos_filename=self.detection_manager.get_custom_filename("POS"),
    wdm_filename=self.detection_manager.get_custom_filename("WDM"),
    flow_filename=self.detection_manager.get_custom_filename("FLOW-SERVICE"),
    lpa_filename=self.detection_manager.get_custom_filename("LPA-SERVICE"),
    sh_filename=self.detection_manager.get_custom_filename("STOREHUB-SERVICE"),
    pos_path=self.detection_manager.detection_config["detection_files"]["POS"],
    wdm_path=self.detection_manager.detection_config["detection_files"]["WDM"],
    flow_path=self.detection_manager.detection_config["detection_files"]["FLOW-SERVICE"],
    lpa_path=self.detection_manager.detection_config["detection_files"]["LPA-SERVICE"],
    sh_path=self.detection_manager.detection_config["detection_files"]["STOREHUB-SERVICE"]
)
                    
                    # Find where to insert the file detection code
                    if not use_hostname_detection:
                        # If hostname detection is disabled, we need to insert after the manual input code
                        insert_marker = "# Print final results"
                    else:
                        # In the updated template, we look for the placeholder for file detection code
                        insert_marker = "# File detection code will be inserted here by the generator"
                    
                    # Find the position to insert the code
                    insert_pos = template.find(insert_marker)
                    if insert_pos != -1:
                        # Insert the detection code at the appropriate position
                        template = template[:insert_pos] + station_detection_code + template[insert_pos + len(insert_marker):]
                        print(f"Added dynamic station detection code to Bash script")
                    else:
                        print(f"Warning: Could not find insertion point for station detection code in Bash script")

            # Write the modified template to the output file
            with open(output_path, 'w', newline='\n') as f:
                f.write(template)
            
            # For Linux scripts, make the file executable
            if platform == "Linux":
                try:
                    os.chmod(output_path, 0o755)  # rwxr-xr-x
                    print(f"Made {output_filename} executable")
                except Exception as e:
                    print(f"Warning: Failed to make {output_filename} executable: {e}")
            
            print(f"Successfully generated {output_filename} at {output_path}")
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error generating installation script: {error_details}")
            raise Exception(f"Failed to generate installation script: {str(e)}")

    def _generate_launcher_templates(self, launchers_dir, config):
        """Generate launcher templates with custom settings from config"""
        # Get settings from config
        pos_settings = config.get("pos_launcher_settings", {})
        wdm_settings = config.get("wdm_launcher_settings", {})
        flow_service_settings = config.get("flow_service_launcher_settings", {})
        lpa_service_settings = config.get("lpa_service_launcher_settings", {})
        storehub_service_settings = config.get("storehub_service_launcher_settings", {})
        
        # Print debug info
        print("Using launcher settings from config:")
        print(f"POS settings: {pos_settings}")
        print(f"WDM settings: {wdm_settings}")
        print(f"FLOW-SERVICE settings: {flow_service_settings}")
        print(f"LPA-SERVICE settings: {lpa_service_settings}")
        print(f"STOREHUB-SERVICE settings: {storehub_service_settings}")
        
        # Define template files
        template_files = {
            "launcher.pos.template": pos_settings,
            "launcher.wdm.template": wdm_settings,
            "launcher.flow-service.template": flow_service_settings,
            "launcher.lpa-service.template": lpa_service_settings,
            "launcher.storehub-service.template": storehub_service_settings
        }
        
        # We'll use templates directly from code instead of trying to find them on disk
        # This avoids path resolution issues when packaged as executable
        for filename, settings in template_files.items():
            # Create template content directly
            template_path = os.path.join(launchers_dir, filename)
            
            # Start with the default template content
            if filename == "launcher.pos.template":
                template_content = """# Launcher defaults for POS
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationJmxPort=
updaterJmxPort=
createShortcuts=0
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
hardware_package_local=
"""
            elif filename == "launcher.wdm.template":
                template_content = """# Launcher defaults for WDM
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8080
applicationServerHttpsPort=8443
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
            elif filename == "launcher.flow-service.template":
                template_content = """# Launcher defaults for Flow Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
            elif filename == "launcher.lpa-service.template":
                template_content = """# Launcher defaults for LPA Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
            elif filename == "launcher.storehub-service.template":
                template_content = """# Launcher defaults for StoreHub Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
applicationJmsPort=7001
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
firebirdServerPath=@FIREBIRD_SERVER_PATH@
firebird_driver_path_local=@FIREBIRD_DRIVER_PATH_LOCAL@
firebirdServerPort=3050
firebirdServerUser=SYSDBA
firebirdServerPassword=masterkey
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
            
            # Now apply settings and save the file
            # Get Firebird server path from config for direct replacement
            firebird_server_path = config.get("firebird_server_path", "")
            # Get the platform from config
            platform_type = config.get("platform", "Windows")
            
            # Process specific replacements for StoreHub Service
            if filename == "launcher.storehub-service.template" and firebird_server_path:
                # Ensure the path is properly formatted for Linux
                if platform_type.lower() == "linux":
                    # Start with a completely clean approach
                    # First, extract just the path parts we need
                    path_parts = []
                    
                    # Split by slashes and process each part
                    for part in firebird_server_path.replace('\\', '/').split('/'):
                        if part and part != "firebird":
                            path_parts.append(part)
                    
                    # For Linux, we want a path like /opt/firebird
                    # Ensure 'opt' is in the path
                    if 'opt' not in path_parts:
                        path_parts = ['opt'] + path_parts
                    
                    # Build the path with a leading slash and no trailing slash
                    firebird_server_path = "/" + "/".join(path_parts)
                    
                    # Finally, ensure it ends with /firebird
                    if not firebird_server_path.endswith('/firebird'):
                        firebird_server_path = firebird_server_path.rstrip('/') + '/firebird'
                    
                    print(f"Normalized Firebird path for Linux: {firebird_server_path}")
                
                print(f"Replacing @FIREBIRD_SERVER_PATH@ with {firebird_server_path} in {filename}")
                template_content = template_content.replace("@FIREBIRD_SERVER_PATH@", firebird_server_path)
            
            # Only apply settings if there are any
            if settings:
                # Update the template with the settings
                lines = template_content.strip().split('\n')
                new_lines = []
                
                for line in lines:
                    if line.startswith('#') or not line.strip():
                        new_lines.append(line)
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        
                        # If this key has a setting
                        if key in settings:
                            # Update the value
                            new_value = settings[key]
                            print(f"Setting {key} to {new_value} in {filename}")
                            new_lines.append(f"{key}={new_value}")
                        else:
                            # Keep the line as is
                            new_lines.append(line)
                    else:
                        # Keep the line as is
                        new_lines.append(line)
                
                template_content = '\n'.join(new_lines)
            else:
                print(f"No settings to apply for {filename}, using default template")
            
            # Write the template to the output file
            try:
                with open(template_path, 'w') as f:
                    f.write(template_content)
                print(f"Generated launcher template: {filename}")
            except Exception as e:
                print(f"Error generating launcher template {filename}: {str(e)}")

    def _generate_onboarding(self, output_dir, config):
        """Generate onboarding script with replaced values based on platform"""
        try:
            # Get platform from config (default to Windows if not specified)
            platform = config.get("platform", "Windows")
            
            # Determine template and output paths based on platform
            if platform == "Windows":
                template_filename = "onboarding.ps1.template"
                output_filename = "onboarding.ps1"
            else:  # Linux
                template_filename = "onboarding.sh.template"
                output_filename = "onboarding.sh"
            
            # Use absolute paths for template and output
            template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", template_filename)
            output_path = os.path.join(output_dir, output_filename)
            
            print(f"Generating {output_filename}:")
            print(f"  Template path: {template_path}")
            print(f"  Output path: {output_path}")
            
            # Check if template exists
            if not os.path.exists(template_path):
                raise Exception(f"Template file not found: {template_path}")
            
            with open(template_path, 'r') as f:
                content = f.read()
            
            # Get configuration values
            base_url = config.get("base_url", "test.cse.cloud4retail.co")
            username = config.get("username", "launchpad")
            form_username = config.get("eh_launchpad_username", "1001")
            tenant_id = config.get("tenant_id", "001")
            
            # Replace configurations based on platform
            if platform == "Windows":
                # Windows-specific replacements
                content = content.replace(
                    'test.cse.cloud4retail.co',
                    base_url
                )
                content = content.replace(
                    '$username = "launchpad"',
                    f'$username = "{username}"'
                )
                content = content.replace(
                    'username = "1001"',
                    f'username = "{form_username}"'
                )
                content = content.replace(
                    '[string]$tenant_id = "001"',
                    f'[string]$tenant_id = "{tenant_id}"'
                )
            else:  # Linux
                # Linux-specific replacements
                content = content.replace(
                    'base_url="test.cse.cloud4retail.co"',
                    f'base_url="{base_url}"'
                )
                content = content.replace(
                    'tenant_id="001"',
                    f'tenant_id="{tenant_id}"'
                )
                content = content.replace(
                    'username="launchpad"',
                    f'username="{username}"'
                )
                content = content.replace(
                    'form_username="1001"',
                    f'form_username="{form_username}"'
                )
            
            # Write the modified content
            with open(output_path, 'w', newline='\n') as f:
                f.write(content)
            
            # For Linux scripts, make the file executable
            if platform == "Linux":
                try:
                    os.chmod(output_path, 0o755)  # rwxr-xr-x
                    print(f"Made {output_filename} executable")
                except Exception as e:
                    print(f"Warning: Failed to make {output_filename} executable: {e}")
                
            print(f"Successfully generated {output_filename} at {output_path}")
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error generating onboarding script: {error_details}")
            raise Exception(f"Failed to generate onboarding script: {str(e)}")

    def _copy_helper_files(self, output_dir, config):
        """Copy helper files to output directory"""
        try:
            # Use absolute paths for source and destination
            script_dir = os.path.dirname(os.path.abspath(__file__))
            helper_src = os.path.join(script_dir, 'helper')
            helper_dst = os.path.join(output_dir, 'helper')
            
            print(f"Copying helper files:")
            print(f"  Source: {helper_src}")
            print(f"  Destination: {helper_dst}")
            
            # Copy store initialization scripts from templates
            templates_dir = os.path.join(script_dir, 'templates')
            platform = config.get("platform", "Windows")
            
            # Get system types from config
            pos_system_type = config.get("pos_system_type", "GKR-OPOS-CLOUD")
            wdm_system_type = config.get("wdm_system_type", "CSE-wdm")
            flow_service_system_type = config.get("flow_service_system_type", "GKR-FLOWSERVICE-CLOUD")
            lpa_service_system_type = config.get("lpa_service_system_type", "CSE-lps-lpa")
            storehub_service_system_type = config.get("storehub_service_system_type", "CSE-sh-cloud")
            base_url = config.get("base_url", "test.cse.cloud4retail.co")
            tenant_id = config.get("tenant_id", "001")
            
            # Copy the appropriate store initialization script based on platform
            if platform == "Windows":
                src_script = os.path.join(templates_dir, "store-initialization.ps1.template")
                dst_script = os.path.join(output_dir, "store-initialization.ps1")
            else:  # Linux
                src_script = os.path.join(templates_dir, "store-initialization.sh.template")
                dst_script = os.path.join(output_dir, "store-initialization.sh")
            
            # Process the template with variables instead of just copying
            if os.path.exists(src_script):
                with open(src_script, 'r') as f:
                    template_content = f.read()
                
                # Replace template variables
                template_content = template_content.replace("${pos_system_type}", pos_system_type)
                template_content = template_content.replace("${wdm_system_type}", wdm_system_type)
                template_content = template_content.replace("${flow_service_system_type}", flow_service_system_type)
                template_content = template_content.replace("${lpa_service_system_type}", lpa_service_system_type)
                template_content = template_content.replace("${storehub_service_system_type}", storehub_service_system_type)
                template_content = template_content.replace("${base_url}", base_url)
                template_content = template_content.replace("${tenant_id}", tenant_id)
                
                # Add user_id replacement from configuration
                user_id = config.get("eh_launchpad_username", "1001")
                template_content = template_content.replace("${user_id}", user_id)
                
                # Write the processed content to the destination file
                with open(dst_script, 'w') as f:
                    f.write(template_content)
                
                print(f"  Generated store initialization script with dynamic system types at: {dst_script}")
                
                # For Linux scripts, make them executable
                if platform == "Linux":
                    try:
                        os.chmod(dst_script, 0o755)  # rwxr-xr-x
                        print(f"  Made {os.path.basename(dst_script)} executable")
                    except Exception as e:
                        print(f"  Warning: Failed to make {os.path.basename(dst_script)} executable: {e}")
            
            # Check if source directory exists
            if not os.path.exists(helper_src):
                # Try to find helper directory in parent directory
                parent_helper = os.path.join(os.path.dirname(script_dir), 'helper')
                if os.path.exists(parent_helper):
                    helper_src = parent_helper
                    print(f"  Found helper directory in parent: {helper_src}")
                else:
                    # Create the required directory structure instead of failing
                    print(f"  Helper directory not found. Creating necessary directory structure.")
                    self._create_helper_structure(helper_dst)
                    
                    # Create password files
                    self._create_password_files(helper_dst, config)
                    
                    # Create init JSON files
                    self._create_init_json_files(helper_dst, config)
                    
                    # Create component-specific files (like create_structure.json)
                    self._create_component_files(helper_dst)
                    
                    # Create launchers directory
                    launchers_dir = os.path.join(helper_dst, 'launchers')
                    os.makedirs(launchers_dir, exist_ok=True)
                    
                    # Generate launcher templates with custom settings
                    self._generate_launcher_templates(launchers_dir, config)
                    
                    print(f"Successfully created helper files at {helper_dst}")
                    return
            
            # Create helper directory if it doesn't exist
            if not os.path.exists(helper_dst):
                os.makedirs(helper_dst, exist_ok=True)
            
            # Ensure all required directories exist in the destination
            for dir_name in self.helper_structure.keys():
                os.makedirs(os.path.join(helper_dst, dir_name), exist_ok=True)
            
            # Copy helper directory structure, excluding launchers directory
            for item in os.listdir(helper_src):
                src_item = os.path.join(helper_src, item)
                dst_item = os.path.join(helper_dst, item)
                
                if item == 'launchers':
                    # Skip launchers directory, we'll handle it separately
                    continue
                    
                if os.path.isdir(src_item):
                    # Create directory if it doesn't exist
                    os.makedirs(dst_item, exist_ok=True)
                    
                    # Copy directory contents
                    for subitem in os.listdir(src_item):
                        src_subitem = os.path.join(src_item, subitem)
                        dst_subitem = os.path.join(dst_item, subitem)
                        if os.path.isdir(src_subitem):
                            if os.path.exists(dst_subitem):
                                shutil.rmtree(dst_subitem)
                            shutil.copytree(src_subitem, dst_subitem)
                        else:
                            shutil.copy2(src_subitem, dst_subitem)
                else:
                    # Copy file
                    shutil.copy2(src_item, dst_item)
            
            # Create launchers directory
            launchers_dir = os.path.join(helper_dst, 'launchers')
            os.makedirs(launchers_dir, exist_ok=True)
            
            # Generate launcher templates with custom settings
            self._generate_launcher_templates(launchers_dir, config)
            
            # Create password files
            self._create_password_files(helper_dst, config)
            
            # Create init JSON files
            self._create_init_json_files(helper_dst, config)
            
            # Create component-specific files (like create_structure.json)
            self._create_component_files(helper_dst)
            
            # Modify JSON files with the correct URLs
            self._modify_json_files(helper_dst, config)
            
            print(f"Successfully copied helper files to {helper_dst}")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error copying helper files: {error_details}")
            raise Exception(f"Failed to copy helper files: {str(e)}")

    def _create_helper_structure(self, helper_dir):
        """Create the necessary helper directory structure with placeholder files"""
        # Create main helper directory
        os.makedirs(helper_dir, exist_ok=True)
        
        # Create sub-directories
        for dir_name in self.helper_structure.keys():
            sub_dir = os.path.join(helper_dir, dir_name)
            os.makedirs(sub_dir, exist_ok=True)
            print(f"  Created directory: {sub_dir}")
        
        # Create component-specific directories and files
        self._create_component_files(helper_dir)

    def _create_component_files(self, helper_dir):
        """Create component-specific directories and files"""
        # Create structure directory and files
        structure_dir = os.path.join(helper_dir, "structure")
        os.makedirs(structure_dir, exist_ok=True)
        print(f"  Created directory: {structure_dir}")
        
        # Create create_structure.json template for all components
        create_structure_json = '''{
    "tenant": {
        "tenantId": "@TENANT_ID@"
    },
    "store": {
        "retailStoreId": "@RETAIL_STORE_ID@"
    },
    "station": {
        "systemName": "@SYSTEM_TYPE@",
        "workstationId": "@WORKSTATION_ID@",
        "name": "@STATION_NAME@"
    },
    "user": "@USER_ID@"
}'''
        
        # Write create_structure.json file
        file_path = os.path.join(structure_dir, "create_structure.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(create_structure_json)
        print(f"  Created structure template: {file_path}")
        
        # Removed creation of empty component directories, as they are now handled by the structure approach

    def _create_default_json_files(self, helper_dir, config):
        """Create default JSON files for onboarding"""
        onboarding_dir = os.path.join(helper_dir, "onboarding")
        os.makedirs(onboarding_dir, exist_ok=True)
        
        # Get user ID from config
        user_id = config.get("eh_launchpad_username", "1001")
        tenant_id = config.get("tenant_id", "001")
        
        # Default JSON templates for different component types
        json_templates = {
            "pos.onboarding.json": '''{"deviceId":"@USER_ID@","tenant_id":"@TENANT_ID@","timestamp":"{{TIMESTAMP}}"}''',
            "wdm.onboarding.json": '''{"deviceId":"@USER_ID@","tenant_id":"@TENANT_ID@","timestamp":"{{TIMESTAMP}}"}''',
            "flow-service.onboarding.json": '''{"deviceId":"@USER_ID@","tenant_id":"@TENANT_ID@","timestamp":"{{TIMESTAMP}}"}''',
            "lpa-service.onboarding.json": '''{"deviceId":"@USER_ID@","tenant_id":"@TENANT_ID@","timestamp":"{{TIMESTAMP}}"}''',
            "storehub-service.onboarding.json": '''{"deviceId":"@USER_ID@","tenant_id":"@TENANT_ID@","timestamp":"{{TIMESTAMP}}"}'''
        }
        
        # Write JSON files
        for filename, content in json_templates.items():
            # Replace placeholders
            timestamp = int(time.time() * 1000)  # Current time in milliseconds
            content = content.replace("{{TIMESTAMP}}", str(timestamp))
            content = content.replace("@TENANT_ID@", tenant_id)
            content = content.replace("@USER_ID@", user_id)
            
            # Write file
            file_path = os.path.join(onboarding_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"  Created JSON file: {file_path}")

    def _create_init_json_files(self, helper_dir, config):
        """Create init JSON files for store configuration"""
        init_dir = os.path.join(helper_dir, "init")
        os.makedirs(init_dir, exist_ok=True)
        
        # Get tenant_id from config
        tenant_id = config.get("tenant_id", "001")
        
        # Create get_store.json template with placeholder for retailStoreId
        store_json_content = '''{
  "station": {
    "systemName": "GKR-Store",
    "tenantId": "''' + tenant_id + '''",
    "retailStoreId": "@RETAIL_STORE_ID@"
  }
}'''
        
        # Write get_store.json file
        file_path = os.path.join(init_dir, "get_store.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(store_json_content)
        print(f"  Created init JSON file: {file_path}")
        
        # Create component-specific directories
        storehub_dir = os.path.join(init_dir, "storehub")
        os.makedirs(storehub_dir, exist_ok=True)
        
        # Get launcher settings for StoreHub
        storehub_settings = {}
        storehub_launcher_settings_key = "storehub_service_launcher_settings"
        
        if storehub_launcher_settings_key in config:
            storehub_settings = config[storehub_launcher_settings_key]
        
        # Get default values or values from launcher settings
        jms_port = storehub_settings.get("applicationJmsPort", "7001")
        firebird_port = storehub_settings.get("firebirdServerPort", "3050")
        firebird_user = storehub_settings.get("firebirdServerUser", "SYSDBA")
        firebird_password = storehub_settings.get("firebirdServerPassword", "masterkey")
        https_port = storehub_settings.get("applicationServerHttpsPort", "8543")
        
        # Get system name from config
        system_name = config.get("storehub_service_system_type", "CSE-sh-cloud")
        
        # Get version from config
        version = "v1.1.0"  # Default version
        if config.get("use_version_override", False):
            version = config.get("storehub_service_version", "v1.1.0")
        else:
            version = config.get("version", "v1.1.0")
        
        # Get the username from config - with debug print
        username = config.get("eh_launchpad_username")
        print(f"Using eh_launchpad_username for StoreHub config: {username}")
        
        # Create update_config.json template with values from launcher settings
        update_config_json_content = '''{
  "levelDescriptor": {
    "structureUniqueName": "@STRUCTURE_UNIQUE_NAME@"
  },
  "systemDescriptor": {
    "systemName": "''' + system_name + '''",
    "systemVersionList": [
      {
        "name": "''' + version + '''"
      }
    ]
  },
  "user": "''' + username + '''",
  "parameterValueChangeList": [
    {
      "name": "activemq.properties",
      "url": "jms-engine.port",
      "value": "''' + jms_port + '''"
    },
    {
      "name": "ds-embedded.properties",
      "url": "datasource.port",
      "value": "''' + firebird_port + '''"
    },
    {
      "name": "ds-embedded.properties",
      "url": "datasource.username",
      "value": "''' + firebird_user + '''"
    },
    {
      "name": "secret.properties",
      "url": "ds-embedded.datasource.password_encrypted",
      "value": "''' + firebird_password + '''"
    },
    {
      "name": "data-router-adapter.properties",
      "url": "swee.common.data-router.adapter.message-adapter.host",
      "value": "@HOSTNAME@"
    },
    {
      "name": "data-router-adapter.properties",
      "url": "swee.common.data-router.adapter.message-adapter.http.port",
      "value": "''' + https_port + '''"
    }
  ]
}'''
        
        # Write update_config.json file for StoreHub
        file_path = os.path.join(storehub_dir, "update_config.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(update_config_json_content)
        print(f"  Created StoreHub config file: {file_path}")

    def _create_password_files(self, helper_dir, config):
        """Create password files for onboarding"""
        try:
            # Create tokens directory
            tokens_dir = os.path.join(helper_dir, "tokens")
            os.makedirs(tokens_dir, exist_ok=True)

            # Create basic auth password file (using launchpad_oauth2)
            basic_auth_password = config.get("launchpad_oauth2", "")
            if basic_auth_password:
                encoded_basic = base64.b64encode(basic_auth_password.encode()).decode()
                basic_auth_path = os.path.join(tokens_dir, "basic_auth_password.txt")
                with open(basic_auth_path, 'w') as f:
                    f.write(encoded_basic)

            # Create form password file (using eh_launchpad_password)
            form_password = config.get("eh_launchpad_password", "")
            if form_password:
                encoded_form = base64.b64encode(form_password.encode()).decode()
                form_password_path = os.path.join(tokens_dir, "form_password.txt")
                with open(form_password_path, 'w') as f:
                    f.write(encoded_form)

        except Exception as e:
            raise Exception(f"Failed to create password files: {str(e)}")

    def _modify_json_files(self, helper_dir, config):
        """Modify JSON files with new configuration"""
        try:
            # Modify all JSON files in onboarding directory
            onboarding_dir = os.path.join(helper_dir, "onboarding")
            if not os.path.exists(onboarding_dir):
                return

            # Get all JSON files in the directory
            json_files = [f for f in os.listdir(onboarding_dir) if f.endswith('.json')]
            
            for json_file in json_files:
                file_path = os.path.join(onboarding_dir, json_file)
                try:
                    with open(file_path, 'r') as f:
                        data = json.loads(f.read())
                    
                    # Recursively replace URLs in the JSON structure
                    self._replace_urls_in_json(data, config['base_url'])
                    
                    # Update specific fields if they exist
                    if "restrictions" in data:
                        data["restrictions"]["tenantId"] = config["tenant_id"]
                    
                    # Write updated JSON with proper formatting
                    with open(file_path, 'w') as f:
                        json.dump(data, f, indent=4)
                        
                except Exception as e:
                    self._show_error(f"Failed to modify {json_file}: {str(e)}")
                    
        except Exception as e:
            raise Exception(f"Failed to modify JSON files: {str(e)}")

    def _replace_urls_in_json(self, data, new_base_url):
        """Recursively replace URLs in JSON structure"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    if 'test.cse.cloud4retail.co' in value:
                        data[key] = value.replace('test.cse.cloud4retail.co', new_base_url)
                else:
                    self._replace_urls_in_json(value, new_base_url)
        elif isinstance(data, list):
            for item in data:
                self._replace_urls_in_json(item, new_base_url)

    def _show_error(self, message):
        """Show error dialog"""
        dialog = ctk.CTkInputDialog(
            text=f"Error: {message}",
            title="Error"
        )
        dialog.destroy()

    def _show_success(self, message):
        """Show success dialog"""
        dialog = ctk.CTkInputDialog(
            text=message,
            title="Success"
        )
        dialog.destroy()

    def _ask_download_dependencies_only(self, component_type, parent=None, error_message=None):
        """Ask user if they want to download dependencies even if component files are not found"""
        import customtkinter as ctk
        import tkinter as tk
        import sys
        
        # Create message based on whether there was an error or just no files found
        if error_message:
            message = f"{component_type} files could not be accessed: {error_message}\n\nWould you like to download Java and Tomcat dependencies anyway?"
        else:
            message = f"No {component_type} files were found.\n\nWould you like to download Java and Tomcat dependencies anyway?"
        
        # Use the parent if provided, otherwise use self.parent_window, or create a new root
        parent_window = parent or self.parent_window
        if parent_window:
            dialog = ctk.CTkToplevel(parent_window)
            dialog.transient(parent_window)  # Make it transient to the parent
        else:
            # Create a temporary root window if no parent is available
            temp_root = tk.Tk()
            temp_root.withdraw()  # Hide the temporary root
            dialog = ctk.CTkToplevel(temp_root)
        
        dialog.title(f"{component_type} Files Not Found")
        dialog.geometry("500x200")
        
        # Force initial update
        dialog.update_idletasks()
        
        # Linux-specific handling
        if sys.platform.startswith('linux'):
            dialog.attributes("-topmost", True)
            dialog.update()
            
        # Center the dialog on the parent window if available
        if parent_window:
            x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - (500 // 2)
            y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - (200 // 2)
            dialog.geometry(f"+{x}+{y}")
        
        # Ensure focus and grab
        dialog.focus_force()
        dialog.grab_set()
        
        # Result variable
        result = False
        
        # Title and message
        ctk.CTkLabel(
            dialog, 
            text=f"{component_type} Files Not Found",
            font=("Helvetica", 16, "bold")
        ).pack(pady=(20, 5), padx=20)
        
        ctk.CTkLabel(
            dialog, 
            text=message,
            font=("Helvetica", 12),
            wraplength=450
        ).pack(pady=(0, 20), padx=20)
        
        # Yes button handler
        def on_yes():
            nonlocal result
            result = True
            dialog.destroy()
            if not parent_window:
                temp_root.destroy()  # Clean up the temporary root if we created one
        
        # No button handler
        def on_no():
            nonlocal result
            result = False
            dialog.destroy()
            if not parent_window:
                temp_root.destroy()  # Clean up the temporary root if we created one
        
        # Buttons
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(fill="x", pady=20, padx=20)
        
        ctk.CTkButton(
            button_frame, 
            text="No", 
            command=on_no, 
            width=100,
            fg_color="#555555",
            hover_color="#333333"
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            button_frame, 
            text="Yes, Download Dependencies", 
            command=on_yes, 
            width=200
        ).pack(side="right", padx=10)
        
        # One more update to ensure everything is displayed
        dialog.update_idletasks()
        
        # Wait for the dialog to close
        if parent_window:
            parent_window.wait_window(dialog)
        else:
            # If we don't have a parent window, use a different approach
            dialog.wait_window()
        
        return result

    def get_component_version(self, system_type, config):
        """Determine the correct version for a component based on its system type"""
        # Get version information from config
        default_version = config.get("version", "v1.0.0")
        use_version_override = config.get("use_version_override", False)
        
        # If version override is disabled, always use the default version
        if not use_version_override:
            return default_version
        
        # If system type is empty, use default version
        if not system_type or system_type == "":
            return default_version
        
        # Print debug information
        print(f"\nDetermining version for system type: {system_type}")
        print(f"Version override enabled: {use_version_override}")
        
        # Match against the exact system type names
        if system_type in ["GKR-OPOS-CLOUD", "CSE-OPOS-CLOUD"]:
            version = config.get("pos_version", default_version)
            print(f"Matched POS system type, using version: {version}")
            return version
        elif system_type in ["CSE-wdm", "GKR-WDM-CLOUD"]:
            version = config.get("wdm_version", default_version)
            print(f"Matched WDM system type, using version: {version}")
            return version
        elif system_type == "GKR-FLOWSERVICE-CLOUD":
            version = config.get("flow_service_version", default_version)
            print(f"Matched Flow Service system type, using version: {version}")
            return version
        elif system_type == "CSE-lps-lpa":
            version = config.get("lpa_service_version", default_version)
            print(f"Matched LPA Service system type, using version: {version}")
            return version
        elif system_type == "CSE-sh-cloud":
            version = config.get("storehub_service_version", default_version)
            print(f"Matched StoreHub Service system type, using version: {version}")
            return version
        else:
            print(f"No match found for system type, using default version: {default_version}")
            return default_version

    def prepare_offline_package(self, config, selected_components, dialog_parent=None):
        try:
            import threading
            import queue
            import time
            
            output_dir = config.get("output_dir", "generated_scripts")
            default_version = config.get("version", "v1.0.0")
            use_version_override = config.get("use_version_override", False)
            
            # Get component-specific versions
            pos_version = config.get("pos_version", default_version)
            wdm_version = config.get("wdm_version", default_version)
            flow_service_version = config.get("flow_service_version", default_version)
            lpa_service_version = config.get("lpa_service_version", default_version)
            storehub_service_version = config.get("storehub_service_version", default_version)
            
            # Get platform dependencies
            platform_dependencies = config.get("platform_dependencies", {})
            
            print(f"\nPreparing offline package:")
            print(f"Output dir: {output_dir}")
            print(f"Default version: {default_version}")
            print(f"Version override enabled: {use_version_override}")
            print(f"POS version: {pos_version}")
            print(f"WDM version: {wdm_version}")
            print(f"Flow Service version: {flow_service_version}")
            print(f"LPA Service version: {lpa_service_version}")
            print(f"StoreHub Service version: {storehub_service_version}")
            print(f"Selected components: {selected_components}")
            print(f"Platform dependencies: {platform_dependencies}")
            
            # Initialize WebDAV browser if not already initialized
            if not self.webdav_browser:
                print("\nInitializing WebDAV browser...")
                self.webdav_browser = self.create_webdav_browser(
                    config["base_url"],
                    config.get("webdav_username"),
                    config.get("webdav_password")
                )
                success, message = self.webdav_browser.connect()
                if not success:
                    raise Exception(f"Failed to connect to WebDAV: {message}")
                print("WebDAV connection successful")
            
            # Create a queue for download results
            download_queue = queue.Queue()
            downloaded_files = []
            download_errors = []
            
            # Helper function to download a file in a separate thread
            def download_file_thread(remote_path, local_path, file_name, component_type):
                try:
                    # Get the full URL for the file
                    webdav_url = f"{self.webdav_browser.options['webdav_hostname']}{remote_path}"
                    auth = (self.webdav_browser.username, self.webdav_browser.password)
                    
                    # Use requests with streaming to track progress
                    with requests.get(webdav_url, auth=auth, stream=True, verify=False) as response:
                        response.raise_for_status()
                        
                        # Get total file size if available
                        total_size = int(response.headers.get('content-length', 0))
                        
                        # Initial progress update
                        download_queue.put(("progress", (file_name, component_type, 0, total_size)))
                        
                        # Open local file for writing
                        with open(local_path, 'wb') as f:
                            downloaded = 0
                            last_update_time = time.time()
                            
                            # Download in chunks and update progress
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    
                                    # Update progress every 0.1 seconds to avoid flooding the queue
                                    current_time = time.time()
                                    if current_time - last_update_time > 0.1:
                                        download_queue.put(("progress", (file_name, component_type, downloaded, total_size)))
                                        last_update_time = current_time
                            
                            # Final progress update
                            download_queue.put(("progress", (file_name, component_type, downloaded, total_size)))
                    
                    # Successfully downloaded
                    download_queue.put(("complete", (file_name, component_type)))
                except Exception as e:
                    print(f"Error downloading {file_name}: {e}")
                    download_queue.put(("error", (file_name, component_type, str(e))))
            
            # Helper function to create a progress dialog
            def create_progress_dialog(parent, total_files):
                import customtkinter as ctk
                import sys
                
                progress_dialog = ctk.CTkToplevel(parent)
                progress_dialog.title("Downloading Files")
                progress_dialog.geometry("700x600")  # Increased size to accommodate multiple progress bars
                progress_dialog.transient(parent)
                
                # Force initial update
                progress_dialog.update_idletasks()
                
                # Linux-specific handling
                if sys.platform.startswith('linux'):
                    progress_dialog.attributes("-topmost", True)
                    progress_dialog.update()
                
                # Center the dialog on the parent window
                x = parent.winfo_x() + (parent.winfo_width() // 2) - (700 // 2)
                y = parent.winfo_y() + (parent.winfo_height() // 2) - (600 // 2)
                progress_dialog.geometry(f"+{x}+{y}")
                
                # Ensure focus and grab
                progress_dialog.focus_force()
                progress_dialog.grab_set()
                
                # Title
                ctk.CTkLabel(
                    progress_dialog,
                    text="Downloading Files",
                    font=("Helvetica", 16, "bold")
                ).pack(pady=(20, 10), padx=20)
                
                # Progress frame
                progress_frame = ctk.CTkFrame(progress_dialog)
                progress_frame.pack(fill="both", expand=True, padx=20, pady=10)
                
                # Overall progress bar
                ctk.CTkLabel(
                    progress_frame,
                    text="Overall Progress:",
                    font=("Helvetica", 12)
                ).pack(pady=(10, 5), padx=10)
                
                progress_bar = ctk.CTkProgressBar(progress_frame, width=650)
                progress_bar.pack(pady=(0, 10), padx=10)
                progress_bar.set(0)
                
                # Files progress label
                files_label = ctk.CTkLabel(
                    progress_frame,
                    text=f"0/{total_files} files completed",
                    font=("Helvetica", 12)
                )
                files_label.pack(pady=(0, 10), padx=10)
                
                # Create a scrollable frame for individual file progress bars
                ctk.CTkLabel(
                    progress_frame,
                    text="Individual File Progress:",
                    font=("Helvetica", 12, "bold")
                ).pack(pady=(10, 5), padx=10, anchor="w")
                
                files_frame = ctk.CTkScrollableFrame(progress_frame, width=650, height=350)
                files_frame.pack(fill="both", expand=True, padx=10, pady=10)
                
                # One more update to ensure everything is displayed 
                progress_dialog.update_idletasks()
                
                # Dictionary to store progress bars and labels for each file
                file_progress_widgets = {}
                
                # We're removing the download log section
                # Return None for log_label since we're not using it anymore
                return progress_dialog, progress_bar, files_label, files_frame, file_progress_widgets, None
            
            # Helper function to prompt user for file selection when multiple JAR files are found
            def prompt_for_file_selection(files, component_type, title=None, description=None, file_type=None, config=None):
                import customtkinter as ctk
                import tkinter as tk
                import sys
                
                # Use default config if not provided
                if config is None:
                    config = {}
                
                # Use custom title and description if provided
                title = title or f"Select {component_type} Installer"
                description = description or f"Please select which installer(s) you want to download:"
                
                # Filter for appropriate file types
                if file_type == "zip":
                    installable_files = [file for file in files if not file['is_directory'] and 
                                        file['name'].endswith('.zip')]
                else:
                    # Get platform from config (default to Windows if not specified)
                    platform = config.get("platform", "Windows")
                    
                    # Filter out Launcher files that don't match the current platform
                    installable_files = []
                    for file in files:
                        if file['is_directory']:
                            continue
                            
                        file_name = file['name']
                        
                        # Include JAR files
                        if file_name.endswith('.jar'):
                            installable_files.append(file)
                        # Include EXE files only for Windows
                        elif file_name.endswith('.exe'):
                            if platform == 'Windows' or not file_name.startswith('Launcher'):
                                installable_files.append(file)
                        # Include RUN files only for Linux
                        elif file_name.endswith('.run'):
                            if platform == 'Linux' or not file_name.startswith('Launcher'):
                                installable_files.append(file)
                
                # Separate Launcher file from other files (only for regular components)
                if file_type != "zip":
                    # Get platform from config (default to Windows if not specified)
                    platform = config.get("platform", "Windows")
                    
                    # Use appropriate launcher filename based on platform
                    launcher_filename = 'Launcher.run' if platform == 'Linux' else 'Launcher.exe'
                    
                    launcher_files = [file for file in installable_files if file['name'] == launcher_filename]
                    other_files = [file for file in installable_files if file['name'] != launcher_filename]
                else:
                    launcher_files = []
                    other_files = installable_files
                
                # If no files found, return empty list
                if len(installable_files) == 0:
                    return []
                
                # If only Launcher.exe or no files, return all files directly
                if file_type != "zip" and len(other_files) == 0:
                    return installable_files
                
                # If only one file (and it's not a dependency), return it directly
                if file_type != "zip" and len(other_files) == 1:
                    return installable_files
                
                # Create a dialog to select files
                # Use the dialog_parent if provided, otherwise use self.parent_window, or create a new root
                parent = dialog_parent or self.parent_window
                if parent:
                    dialog = ctk.CTkToplevel(parent)
                    dialog.transient(parent)  # Make it transient to the parent
                else:
                    # Create a temporary root window if no parent is available
                    temp_root = tk.Tk()
                    temp_root.withdraw()  # Hide the temporary root
                    dialog = ctk.CTkToplevel(temp_root)
                
                dialog.title(title)
                dialog.geometry("600x500")  # Increased size for better visibility
                
                # Force initial update for Linux
                dialog.update_idletasks()
                
                # Linux-specific handling
                if sys.platform.startswith('linux'):
                    dialog.attributes("-topmost", True)
                    dialog.update()
                    
                # Focus and grab management
                dialog.focus_force()
                dialog.grab_set()
                
                # Center the dialog on the parent window if available
                if parent:
                    x = parent.winfo_x() + (parent.winfo_width() // 2) - (600 // 2)
                    y = parent.winfo_y() + (parent.winfo_height() // 2) - (500 // 2)
                    dialog.geometry(f"+{x}+{y}")
                
                # Title and description
                ctk.CTkLabel(
                    dialog, 
                    text=title,
                    font=("Helvetica", 16, "bold")
                ).pack(pady=(20, 5), padx=20)
                
                ctk.CTkLabel(
                    dialog, 
                    text=description,
                    font=("Helvetica", 12)
                ).pack(pady=(0, 20), padx=20)
                
                # If Launcher.exe exists, show a message that it will be downloaded automatically
                if launcher_files:
                    # Get platform from config (default to Windows if not specified)
                    platform = config.get("platform", "Windows")
                    
                    # Use appropriate launcher filename based on platform
                    launcher_filename = 'Launcher.run' if platform == 'Linux' else 'Launcher.exe'
                    
                    launcher_label = ctk.CTkLabel(
                        dialog,
                        text=f"Note: {launcher_filename} will be downloaded automatically",
                        font=("Helvetica", 12, "italic"),
                        text_color="gray"
                    )
                    launcher_label.pack(pady=(0, 10), padx=20)
                
                # Create a scrollable frame for the checkboxes
                scroll_frame = ctk.CTkScrollableFrame(dialog, width=450, height=200)
                scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
                
                # Update to ensure scroll_frame is properly rendered
                dialog.update_idletasks()
                
                # Find the latest version (assuming version numbers are in the filenames)
                # This is a simple heuristic - we'll try to find the file with the highest version number
                latest_file = None
                
                # First, try to find files with version numbers in format x.y.z
                import re
                version_pattern = re.compile(r'(\d+\.\d+\.\d+)')
                versioned_files = []
                
                for file in other_files:
                    match = version_pattern.search(file['name'])
                    if match:
                        version = match.group(1)
                        versioned_files.append((file, version))
                
                if versioned_files:
                    # Sort by version number (as string, which works for simple version formats)
                    versioned_files.sort(key=lambda x: [int(n) for n in x[1].split('.')])
                    latest_file = versioned_files[-1][0]  # Get the file with the highest version
                
                # If no versioned files found, try to use date in filename or just pick the last file
                if not latest_file:
                    # Try to find date patterns (YYYYMMDD or similar)
                    date_pattern = re.compile(r'(\d{8}|\d{6})')
                    dated_files = []
                    
                    for file in other_files:
                        match = date_pattern.search(file['name'])
                        if match:
                            date = match.group(1)
                            dated_files.append((file, date))
                    
                    if dated_files:
                        # Sort by date (as string)
                        dated_files.sort(key=lambda x: x[1])
                        latest_file = dated_files[-1][0]  # Get the file with the latest date
                    else:
                        # If all else fails, just pick the last file in the list
                        # Sort alphabetically first to ensure consistent behavior
                        sorted_files = sorted(other_files, key=lambda x: x['name'])
                        latest_file = sorted_files[-1] if sorted_files else None
                
                # Create variables to track selections
                selected_vars = {}
                
                # For Java files, identify the latest version for each platform
                latest_windows_java = None
                latest_linux_java = None
                
                if component_type and 'Java' in component_type:
                    # Get platform from config
                    platform = config.get("platform", "Windows")
                    print(f"Current platform for Java selection: {platform}")
                    
                    # Find all Java files for each platform
                    windows_java_files = []
                    linux_java_files = []
                    
                    for file in other_files:
                        file_name = file['name'].lower()
                        if "java" in component_type.lower():
                            # Collect Windows Java files - check both zuludk and zulujre patterns
                            if ("windows" in file_name and 
                                ("zulujdk" in file_name or "zuludk" in file_name or "zulujre" in file_name)):
                                print(f"Found Windows Java file: {file['name']}")
                                windows_java_files.append(file)
                            # Collect Linux Java files - check both zuludk and zulujre patterns
                            elif ("linux" in file_name and 
                                  ("zulujdk" in file_name or "zuludk" in file_name or "zulujre" in file_name)):
                                print(f"Found Linux Java file: {file['name']}")
                                linux_java_files.append(file)
                    
                    # Parse version numbers for better sorting
                    import re
                    
                    def extract_version(filename):
                        # Extract version like 11.0.18 or 1.8.0_362
                        version_match = re.search(r'(\d+\.\d+\.\d+(?:_\d+)?)', filename)
                        if version_match:
                            version_str = version_match.group(1)
                            # Convert to tuple for comparison
                            if '_' in version_str:
                                # Handle Java 8 style (1.8.0_362)
                                main_version, update = version_str.split('_')
                                parts = main_version.split('.')
                                return (int(parts[0]), int(parts[1]), int(parts[2]), int(update))
                            else:
                                # Handle Java 11+ style (11.0.18)
                                parts = version_str.split('.')
                                return tuple(int(p) for p in parts)
                        return (0, 0, 0)  # Default if no version found
                    
                    # Sort Windows Java files by version
                    if windows_java_files:
                        # Sort by parsed version numbers
                        windows_java_files.sort(key=lambda x: extract_version(x['name']))
                        latest_windows_java = windows_java_files[-1]
                        print(f"Latest Windows Java: {latest_windows_java['name']}")
                    
                    # Sort Linux Java files by version
                    if linux_java_files:
                        # Sort by parsed version numbers
                        linux_java_files.sort(key=lambda x: extract_version(x['name']))
                        latest_linux_java = linux_java_files[-1]
                        print(f"Latest Linux Java: {latest_linux_java['name']}")
                
                for file in other_files:
                    # Default to not selected
                    default_selected = False
                    
                    # For Java files, select based on platform
                    if component_type and 'Java' in component_type:
                        platform = config.get("platform", "Windows")
                        file_name = file['name'].lower()
                        
                        # For Windows platform, select the latest Windows Java
                        if platform == "Windows":
                            if latest_windows_java and file['name'] == latest_windows_java['name']:
                                print(f"Pre-selecting Windows Java: {file['name']}")
                                default_selected = True
                        # For Linux platform, select the latest Linux Java
                        elif platform == "Linux":
                            if latest_linux_java and file['name'] == latest_linux_java['name']:
                                print(f"Pre-selecting Linux Java: {file['name']}")
                                default_selected = True
                    # For non-Java files, use the latest file logic
                    elif file == latest_file:
                        default_selected = True
                    
                    var = ctk.BooleanVar(value=default_selected)
                    selected_vars[file['name']] = var
                    checkbox = ctk.CTkCheckBox(
                        scroll_frame, 
                        text=file['name'], 
                        variable=var,
                        checkbox_width=20,
                        checkbox_height=20
                    )
                    checkbox.pack(anchor="w", pady=5, padx=10)
                
                # Add select all / deselect all buttons
                buttons_frame = ctk.CTkFrame(dialog)
                buttons_frame.pack(fill="x", pady=(0, 10), padx=20)
                
                def select_all():
                    for var in selected_vars.values():
                        var.set(True)
                
                def deselect_all():
                    for var in selected_vars.values():
                        var.set(False)
                
                ctk.CTkButton(
                    buttons_frame,
                    text="Select All",
                    command=select_all,
                    width=100,
                    height=25,
                    fg_color="#555555",
                    hover_color="#333333"
                ).pack(side="left", padx=5)
                
                ctk.CTkButton(
                    buttons_frame,
                    text="Deselect All",
                    command=deselect_all,
                    width=100,
                    height=25,
                    fg_color="#555555",
                    hover_color="#333333"
                ).pack(side="left", padx=5)
                
                # Result variable
                result = []
                
                # OK button handler
                def on_ok():
                    nonlocal result
                    # Always include Launcher.exe files
                    result = launcher_files.copy()
                    # Add selected non-Launcher files
                    result.extend([file for file in other_files if selected_vars[file['name']].get()])
                    dialog.destroy()
                    if not parent:
                        temp_root.destroy()  # Clean up the temporary root if we created one
                
                # Cancel button handler
                def on_cancel():
                    nonlocal result
                    # Always include Launcher.exe files even on cancel
                    result = launcher_files.copy()
                    dialog.destroy()
                    if not parent:
                        temp_root.destroy()  # Clean up the temporary root if we created one
                
                # Buttons
                button_frame = ctk.CTkFrame(dialog)
                button_frame.pack(fill="x", pady=20, padx=20)
                
                ctk.CTkButton(
                    button_frame, 
                    text="Cancel", 
                    command=on_cancel, 
                    width=100,
                    fg_color="#555555",
                    hover_color="#333333"
                ).pack(side="left", padx=10)
                
                ctk.CTkButton(
                    button_frame, 
                    text="Download Selected", 
                    command=on_ok, 
                    width=150
                ).pack(side="right", padx=10)
                
                # Wait for the dialog to close
                if parent:
                    parent.wait_window(dialog)
                else:
                    # If we don't have a parent window, use a different approach
                    dialog.wait_window()
                
                return result
            
            # Helper function to download dependencies for a component
            def download_dependencies_for_component(component_type, component_dir):
                dependency_files = []
                
                # Get parent directory (one level up from component_dir)
                parent_dir = os.path.dirname(component_dir)
                
                # Process Java
                java_path = "/SoftwarePackage/Java"
                print(f"\nChecking Java directory for {component_type}: {java_path}")
                
                try:
                    # Create Java directory at the same level as component directories
                    java_dir = os.path.join(parent_dir, "Java")
                    os.makedirs(java_dir, exist_ok=True)
                    
                    # Check if Java files already exist
                    existing_java_files = [f for f in os.listdir(java_dir) if f.endswith('.zip')]
                    download_java = True
                    
                    if existing_java_files:
                        # Ask user if they want to download Java again
                        download_java = self._ask_download_again(f"{component_type} Java", existing_java_files, dialog_parent)
                        if not download_java:
                            print(f"Skipping Java download for {component_type} as files already exist")
                    
                    if download_java:
                        java_files = self.webdav_browser.list_directories(java_path)
                        print(f"Found Java files: {java_files}")
                        
                        # Prompt user to select Java version
                        selected_java_files = prompt_for_file_selection(
                            java_files, 
                            f"{component_type} Java", 
                            f"Select Java Version for {component_type}", 
                            f"Please select which Java version to download for {component_type}:",
                            "zip",
                            config
                        )
                        
                        # Add selected files to dependency files list
                        for file in selected_java_files:
                            file_name = file['name']
                            remote_path = f"{java_path}/{file_name}"
                            local_path = os.path.join(java_dir, file_name)
                            dependency_files.append((remote_path, local_path, file_name, f"{component_type} Java"))
                
                except Exception as e:
                    print(f"Error accessing Java directory: {e}")
                    download_errors.append(f"Failed to access Java directory for {component_type}: {str(e)}")
                
                # Process Tomcat
                tomcat_path = "/SoftwarePackage/Tomcat"
                print(f"\nChecking Tomcat directory for {component_type}: {tomcat_path}")
                
                try:
                    # Create Tomcat directory at the same level as component directories
                    tomcat_dir = os.path.join(parent_dir, "Tomcat")
                    os.makedirs(tomcat_dir, exist_ok=True)
                    
                    # Check if Tomcat files already exist
                    existing_tomcat_files = [f for f in os.listdir(tomcat_dir) if f.endswith('.zip')]
                    download_tomcat = True
                    
                    if existing_tomcat_files:
                        # Ask user if they want to download Tomcat again
                        download_tomcat = self._ask_download_again(f"{component_type} Tomcat", existing_tomcat_files, dialog_parent)
                        if not download_tomcat:
                            print(f"Skipping Tomcat download for {component_type} as files already exist")
                    
                    if download_tomcat:
                        tomcat_files = self.webdav_browser.list_directories(tomcat_path)
                        print(f"Found Tomcat files: {tomcat_files}")
                        
                        # Prompt user to select Tomcat version
                        selected_tomcat_files = prompt_for_file_selection(
                            tomcat_files, 
                            f"{component_type} Tomcat", 
                            f"Select Tomcat Version for {component_type}", 
                            f"Please select which Tomcat version to download for {component_type}:",
                            "zip",
                            config
                        )
                        
                        # Add selected files to dependency files list
                        for file in selected_tomcat_files:
                            file_name = file['name']
                            remote_path = f"{tomcat_path}/{file_name}"
                            local_path = os.path.join(tomcat_dir, file_name)
                            dependency_files.append((remote_path, local_path, file_name, f"{component_type} Tomcat"))
                
                except Exception as e:
                    print(f"Error accessing Tomcat directory: {e}")
                    download_errors.append(f"Failed to access Tomcat directory for {component_type}: {str(e)}")
                
                # Process Jaybird if selected
                if platform_dependencies.get("JAYBIRD", False):
                    print(f"\nProcessing Jaybird platform dependency...")
                    jaybird_dir = os.path.join(parent_dir, "Jaybird")
                    os.makedirs(jaybird_dir, exist_ok=True)
                    
                    jaybird_path = "/SoftwarePackage/Drivers"
                    print(f"Checking Jaybird directory: {jaybird_path}")
                    
                    try:
                        # Check if Jaybird files already exist
                        existing_jaybird_files = [f for f in os.listdir(jaybird_dir) if f.endswith('.jar')]
                        download_jaybird = True
                        
                        if existing_jaybird_files:
                            # Ask user if they want to download Jaybird again
                            download_jaybird = self._ask_download_again("Jaybird", existing_jaybird_files, dialog_parent)
                            if not download_jaybird:
                                print(f"Skipping Jaybird download as files already exist")
                        
                        if download_jaybird:
                            jaybird_files = self.webdav_browser.list_directories(jaybird_path)
                            print(f"Found Jaybird files: {jaybird_files}")
                            
                            # Filter for .jar files only
                            jaybird_files = [f for f in jaybird_files if f.get('name', '').endswith('.jar')]
                            
                            if jaybird_files:
                                # Prompt user to select Jaybird version
                                selected_jaybird_files = prompt_for_file_selection(
                                    jaybird_files, 
                                    "Jaybird", 
                                    "Select Jaybird Version", 
                                    "Please select which Jaybird driver to download:",
                                    "jar",
                                    config
                                )
                                
                                # Add selected files to download list
                                for file in selected_jaybird_files:
                                    file_name = file['name']
                                    remote_path = f"{jaybird_path}/{file_name}"
                                    local_path = os.path.join(jaybird_dir, file_name)
                                    dependency_files.append((remote_path, local_path, file_name, "Jaybird"))
                            else:
                                print("No Jaybird .jar files found in the Drivers directory")
                                download_errors.append("No Jaybird .jar files found in the Drivers directory")
                    
                    except Exception as e:
                        print(f"Error accessing Jaybird directory: {e}")
                        download_errors.append(f"Failed to access Jaybird directory: {str(e)}")
                        
                return dependency_files
            
            # Collect all files to download first
            files_to_download = []
            
            # Process Java if selected
            if platform_dependencies.get("JAVA", False):
                print(f"\nProcessing Java platform dependency...")
                java_dir = os.path.join(output_dir, "Java")
                os.makedirs(java_dir, exist_ok=True)
                
                java_path = "/SoftwarePackage/Java"
                print(f"Checking Java directory: {java_path}")
                
                try:
                    # Check if Java files already exist
                    existing_java_files = [f for f in os.listdir(java_dir) if f.endswith('.zip')]
                    download_java = True
                    
                    if existing_java_files:
                        # Ask user if they want to download Java again
                        download_java = self._ask_download_again("Java", existing_java_files, dialog_parent)
                        if not download_java:
                            print(f"Skipping Java download as files already exist")
                    
                    if download_java:
                        java_files = self.webdav_browser.list_directories(java_path)
                        print(f"Found Java files: {java_files}")
                        
                        # Prompt user to select Java version
                        selected_java_files = prompt_for_file_selection(
                            java_files, 
                            "Java", 
                            "Select Java Version", 
                            "Please select which Java version to download:",
                            "zip",
                            config
                        )
                        
                        # Add selected files to download list
                        for file in selected_java_files:
                            file_name = file['name']
                            remote_path = f"{java_path}/{file_name}"
                            local_path = os.path.join(java_dir, file_name)
                            files_to_download.append((remote_path, local_path, file_name, "Java"))
                
                except Exception as e:
                    print(f"Error accessing Java directory: {e}")
                    download_errors.append(f"Failed to access Java directory: {str(e)}")
            
            # Process Tomcat if selected
            if platform_dependencies.get("TOMCAT", False):
                print(f"\nProcessing Tomcat platform dependency...")
                tomcat_dir = os.path.join(output_dir, "Tomcat")
                os.makedirs(tomcat_dir, exist_ok=True)
                
                tomcat_path = "/SoftwarePackage/Tomcat"
                print(f"Checking Tomcat directory: {tomcat_path}")
                
                try:
                    # Check if Tomcat files already exist
                    existing_tomcat_files = [f for f in os.listdir(tomcat_dir) if f.endswith('.zip')]
                    download_tomcat = True
                    
                    if existing_tomcat_files:
                        # Ask user if they want to download Tomcat again
                        download_tomcat = self._ask_download_again("Tomcat", existing_tomcat_files, dialog_parent)
                        if not download_tomcat:
                            print(f"Skipping Tomcat download as files already exist")
                    
                    if download_tomcat:
                        tomcat_files = self.webdav_browser.list_directories(tomcat_path)
                        print(f"Found Tomcat files: {tomcat_files}")
                        
                        # Prompt user to select Tomcat version
                        selected_tomcat_files = prompt_for_file_selection(
                            tomcat_files, 
                            "Tomcat", 
                            "Select Tomcat Version", 
                            "Please select which Tomcat version to download:",
                            "zip",
                            config
                        )
                        
                        # Add selected files to download list
                        for file in selected_tomcat_files:
                            file_name = file['name']
                            remote_path = f"{tomcat_path}/{file_name}"
                            local_path = os.path.join(tomcat_dir, file_name)
                            files_to_download.append((remote_path, local_path, file_name, "Tomcat"))
                
                except Exception as e:
                    print(f"Error accessing Tomcat directory: {e}")
                    download_errors.append(f"Failed to access Tomcat directory: {str(e)}")
            
            # Process Jaybird if selected
            if platform_dependencies.get("JAYBIRD", False):
                print(f"\nProcessing Jaybird platform dependency...")
                jaybird_dir = os.path.join(output_dir, "Jaybird")
                os.makedirs(jaybird_dir, exist_ok=True)
                
                jaybird_path = "/SoftwarePackage/Drivers"
                print(f"Checking Jaybird directory: {jaybird_path}")
                
                try:
                    # Check if Jaybird files already exist
                    existing_jaybird_files = [f for f in os.listdir(jaybird_dir) if f.endswith('.jar')]
                    download_jaybird = True
                    
                    if existing_jaybird_files:
                        # Ask user if they want to download Jaybird again
                        download_jaybird = self._ask_download_again("Jaybird", existing_jaybird_files, dialog_parent)
                        if not download_jaybird:
                            print(f"Skipping Jaybird download as files already exist")
                    
                    if download_jaybird:
                        jaybird_files = self.webdav_browser.list_directories(jaybird_path)
                        print(f"Found Jaybird files: {jaybird_files}")
                        
                        # Filter for .jar files only
                        jaybird_files = [f for f in jaybird_files if f.get('name', '').endswith('.jar')]
                        
                        if jaybird_files:
                            # Prompt user to select Jaybird version
                            selected_jaybird_files = prompt_for_file_selection(
                                jaybird_files, 
                                "Jaybird", 
                                "Select Jaybird Version", 
                                "Please select which Jaybird driver to download:",
                                "jar",
                                config
                            )
                            
                            # Add selected files to download list
                            for file in selected_jaybird_files:
                                file_name = file['name']
                                remote_path = f"{jaybird_path}/{file_name}"
                                local_path = os.path.join(jaybird_dir, file_name)
                                files_to_download.append((remote_path, local_path, file_name, "Jaybird"))
                        else:
                            print("No Jaybird .jar files found in the Drivers directory")
                            download_errors.append("No Jaybird .jar files found in the Drivers directory")
                
                except Exception as e:
                    print(f"Error accessing Jaybird directory: {e}")
                    download_errors.append(f"Failed to access Jaybird directory: {str(e)}")
                        
            # Process all selected components
            if "POS" in selected_components:
                pos_dir = os.path.join(output_dir, "offline_package_POS")
                print(f"\nProcessing POS component...")
                print(f"Output directory: {pos_dir}")
                os.makedirs(pos_dir, exist_ok=True)
                
                # Determine system type and version first
                pos_system_type = config.get("pos_system_type", "CSE-OPOS-CLOUD")
                version_to_use = self.get_component_version(pos_system_type, config)
                
                print(f"Using system type: {pos_system_type}")
                print(f"Using version: {version_to_use}")
                
                # Navigate to version directory with correct system type and version
                pos_version_path = f"/SoftwarePackage/{pos_system_type}/{version_to_use}"
                print(f"Checking version directory: {pos_version_path}")
                
                try:
                    files = self.webdav_browser.list_directories(pos_version_path)
                    print(f"Found files: {files}")
                    
                    # Prompt user to select files if multiple JAR/EXE files are found
                    selected_files = prompt_for_file_selection(files, "POS", config=config)
                    
                    # Add selected files to download list
                    for file in selected_files:
                        file_name = file['name']
                        remote_path = f"{pos_version_path}/{file_name}"
                        local_path = os.path.join(pos_dir, file_name)
                        
                        # Make launcher names more specific by adding component name
                        display_name = file_name
                        if file_name.startswith("Launcher."):
                            display_name = f"POS {file_name}"
                        
                        files_to_download.append((remote_path, local_path, display_name, "POS"))
                    
                    # We don't download Java and Tomcat as dependencies here anymore
                    # They should be downloaded once as standalone components if needed
                
                except Exception as e:
                    print(f"Error accessing POS version directory: {e}")
                    raise
                
                # We're removing the launcher template copying code
            
            # Process WDM component
            if "WDM" in selected_components:
                wdm_dir = os.path.join(output_dir, "offline_package_WDM")
                print(f"\nProcessing WDM component...")
                print(f"Output directory: {wdm_dir}")
                os.makedirs(wdm_dir, exist_ok=True)
                
                # Determine system type and version first
                wdm_system_type = config.get("wdm_system_type", "CSE-wdm")
                version_to_use = self.get_component_version(wdm_system_type, config)
                
                print(f"Using system type: {wdm_system_type}")
                print(f"Using version: {version_to_use}")
                
                # Navigate to version directory with correct system type and version
                wdm_version_path = f"/SoftwarePackage/{wdm_system_type}/{version_to_use}"
                print(f"Checking version directory: {wdm_version_path}")
                
                try:
                    files = self.webdav_browser.list_directories(wdm_version_path)
                    print(f"Found files: {files}")
                    
                    # Prompt user to select files if multiple JAR/EXE files are found
                    selected_files = prompt_for_file_selection(files, "WDM", config=config)
                    
                    # Add selected files to download list
                    for file in selected_files:
                        file_name = file['name']
                        remote_path = f"{wdm_version_path}/{file_name}"
                        local_path = os.path.join(wdm_dir, file_name)
                        
                        # Make launcher names more specific by adding component name
                        display_name = file_name
                        if file_name.startswith("Launcher."):
                            display_name = f"WDM {file_name}"
                        
                        files_to_download.append((remote_path, local_path, display_name, "WDM"))
                    
                except Exception as e:
                    print(f"Error accessing WDM version directory: {e}")
                    raise
                
                # We're removing the launcher template copying code
            
            # Process Flow Service component
            if "FLOW-SERVICE" in selected_components:
                flow_service_dir = os.path.join(output_dir, "offline_package_FLOW-SERVICE")
                print(f"\nProcessing Flow Service component...")
                print(f"Output directory: {flow_service_dir}")
                os.makedirs(flow_service_dir, exist_ok=True)
                
                # Determine system type and version first
                flow_service_system_type = config.get("flow_service_system_type", "GKR-FLOWSERVICE-CLOUD")
                version_to_use = self.get_component_version(flow_service_system_type, config)
                
                print(f"Using system type: {flow_service_system_type}")
                print(f"Using version: {version_to_use}")
                
                # Navigate to version directory with correct system type and version
                flow_service_version_path = f"/SoftwarePackage/{flow_service_system_type}/{version_to_use}"
                print(f"Checking version directory: {flow_service_version_path}")
                
                try:
                    files = self.webdav_browser.list_directories(flow_service_version_path)
                    print(f"Found files: {files}")
                    
                    # Prompt user to select files if multiple JAR/EXE files are found
                    selected_files = prompt_for_file_selection(files, "Flow Service", config=config)
                    
                    # Add selected files to download list
                    for file in selected_files:
                        file_name = file['name']
                        remote_path = f"{flow_service_version_path}/{file_name}"
                        local_path = os.path.join(flow_service_dir, file_name)
                        
                        # Make launcher names more specific by adding component name
                        display_name = file_name
                        if file_name.startswith("Launcher."):
                            display_name = f"Flow Service {file_name}"
                        
                        files_to_download.append((remote_path, local_path, display_name, "Flow Service"))
                    
                except Exception as e:
                    print(f"Error accessing Flow Service version directory: {e}")
                    raise
                
                # We're removing the launcher template copying code
            
            # Process LPA Service component
            if "LPA-SERVICE" in selected_components:
                lpa_service_dir = os.path.join(output_dir, "offline_package_LPA")
                print(f"\nProcessing LPA Service component...")
                print(f"Output directory: {lpa_service_dir}")
                os.makedirs(lpa_service_dir, exist_ok=True)
                
                # Determine system type and version first
                lpa_service_system_type = config.get("lpa_service_system_type", "CSE-lps-lpa")
                version_to_use = self.get_component_version(lpa_service_system_type, config)
                
                print(f"Using system type: {lpa_service_system_type}")
                print(f"Using version: {version_to_use}")
                
                # Navigate to version directory with correct system type and version
                lpa_service_version_path = f"/SoftwarePackage/{lpa_service_system_type}/{version_to_use}"
                print(f"Checking version directory: {lpa_service_version_path}")
                
                try:
                    files = self.webdav_browser.list_directories(lpa_service_version_path)
                    print(f"Found files: {files}")
                    
                    # Prompt user to select files if multiple JAR/EXE files are found
                    selected_files = prompt_for_file_selection(files, "LPA Service", config=config)
                    
                    # Add selected files to download list
                    for file in selected_files:
                        file_name = file['name']
                        remote_path = f"{lpa_service_version_path}/{file_name}"
                        local_path = os.path.join(lpa_service_dir, file_name)
                        
                        # Make launcher names more specific by adding component name
                        display_name = file_name
                        if file_name.startswith("Launcher."):
                            display_name = f"LPA Service {file_name}"
                        
                        files_to_download.append((remote_path, local_path, display_name, "LPA Service"))
                    
                except Exception as e:
                    print(f"Error accessing LPA Service version directory: {e}")
                    raise
                
                # We're removing the launcher template copying code
            
            # Process StoreHub Service component
            if "STOREHUB-SERVICE" in selected_components:
                storehub_service_dir = os.path.join(output_dir, "offline_package_SH")
                print(f"\nProcessing StoreHub Service component...")
                print(f"Output directory: {storehub_service_dir}")
                os.makedirs(storehub_service_dir, exist_ok=True)
                
                # Determine system type and version first
                storehub_service_system_type = config.get("storehub_service_system_type", "CSE-sh-cloud")
                version_to_use = self.get_component_version(storehub_service_system_type, config)
                
                print(f"Using system type: {storehub_service_system_type}")
                print(f"Using version: {version_to_use}")
                
                # Navigate to version directory with correct system type and version
                storehub_service_version_path = f"/SoftwarePackage/{storehub_service_system_type}/{version_to_use}"
                print(f"Checking version directory: {storehub_service_version_path}")
                
                try:
                    files = self.webdav_browser.list_directories(storehub_service_version_path)
                    print(f"Found files: {files}")
                    
                    # Prompt user to select files if multiple JAR/EXE files are found
                    selected_files = prompt_for_file_selection(files, "StoreHub Service", config=config)
                    
                    # Add selected files to download list
                    for file in selected_files:
                        file_name = file['name']
                        remote_path = f"{storehub_service_version_path}/{file_name}"
                        local_path = os.path.join(storehub_service_dir, file_name)
                        
                        # Make launcher names more specific by adding component name
                        display_name = file_name
                        if file_name.startswith("Launcher."):
                            display_name = f"StoreHub Service {file_name}"
                        
                        files_to_download.append((remote_path, local_path, display_name, "StoreHub Service"))
                    
                except Exception as e:
                    print(f"Error accessing StoreHub Service version directory: {e}")
                    raise
                
                # We're removing the launcher template copying code
            
            # If no files to download, return
            if not files_to_download:
                return False, "No files were selected for download"
            
            # Create progress dialog
            parent = dialog_parent or self.parent_window
            if parent:
                progress_dialog, progress_bar, files_label, files_frame, file_progress_widgets, _ = create_progress_dialog(parent, len(files_to_download))
            
            # Start download threads
            download_threads = []
            for remote_path, local_path, file_name, component_type in files_to_download:
                thread = threading.Thread(
                    target=download_file_thread,
                    args=(remote_path, local_path, file_name, component_type)
                )
                thread.daemon = True
                thread.start()
                download_threads.append(thread)
            
            # Initialize tracking variables
            completed_files = 0
            file_progress = {}  # Track progress for each file
            total_bytes = 0
            downloaded_bytes = 0
            
            # Flag to track if dialog is still open
            dialog_closed = [False]  # Using a list to allow modification in nested functions
            
            # Store references to UI elements that need to be accessed later
            float_windows = [None]  # To store the floating window reference
            downloads_cancelled = [False]  # To track if downloads are cancelled
            
            # Define cancel_downloads function first - make it simpler and more robust
            def cancel_downloads(*args):
                # Set the cancelled flag first
                downloads_cancelled[0] = True
                
                # Force the loop to end by setting completed_files
                nonlocal completed_files
                completed_files = len(files_to_download)
                
                # Clear the download queue
                while not download_queue.empty():
                    try:
                        download_queue.get_nowait()
                    except:
                        pass
                
                # Destroy the floating window if it exists
                if float_windows[0] is not None:
                    try:
                        float_windows[0].destroy()
                    except:
                        pass
                
                # Make sure the main progress dialog is destroyed
                try:
                    progress_dialog.destroy()
                except:
                    pass
                
                # Show cancellation message
                try:
                    import tkinter.messagebox as messagebox
                    messagebox.showinfo("Downloads Cancelled", "Download process has been cancelled.")
                except:
                    pass
                
                return True  # Return True to allow the window to close
            
            # Create a function to process the download queue in the main thread
            def process_download_queue():
                nonlocal completed_files, downloaded_bytes, total_bytes
                
                # Check if downloads were cancelled
                if downloads_cancelled[0]:
                    return
                
                # Process a limited number of items from the queue to keep UI responsive
                queue_items_processed = 0
                max_items_per_cycle = 10
                
                while not download_queue.empty() and queue_items_processed < max_items_per_cycle:
                    try:
                        status, data = download_queue.get_nowait()
                        queue_items_processed += 1
                        
                        # Skip updates if dialog was closed
                        if dialog_closed[0]:
                            continue
                        
                        if status == "progress":
                            # Update file progress
                            file_name, component_type, downloaded, total = data
                            
                            # Store the progress in the file_progress dictionary
                            file_progress[file_name] = (downloaded, total)
                            
                            # Create progress bar for this file if it doesn't exist yet
                            if file_name not in file_progress_widgets:
                                file_frame = ctk.CTkFrame(files_frame)
                                file_frame.pack(fill="x", padx=10, pady=(0, 5))
                                
                                file_label = ctk.CTkLabel(file_frame, text=f"{file_name} ({component_type})", anchor="w")
                                file_label.pack(side="top", fill="x")
                                
                                file_progress_bar = ctk.CTkProgressBar(file_frame, width=400)
                                file_progress_bar.pack(side="top", fill="x", pady=(0, 5))
                                file_progress_bar.set(0)
                                
                                file_progress_widgets[file_name] = (file_frame, file_label, file_progress_bar)
                            
                            # Update progress bar for this file
                            _, _, file_progress_bar = file_progress_widgets[file_name]
                            if total > 0:
                                progress_value = downloaded / total
                                file_progress_bar.set(progress_value)
                            
                            # Calculate and update total progress
                            nonlocal downloaded_bytes, total_bytes
                            downloaded_bytes = sum(d for d, _ in file_progress.values())
                            total_bytes = sum(t for _, t in file_progress.values() if t > 0)
                            
                            if total_bytes > 0:
                                # Calculate overall percentage for the label
                                overall_percentage = downloaded_bytes / total_bytes * 100
                                
                                # Update the main progress bar
                                progress_value = downloaded_bytes / total_bytes
                                progress_bar.set(progress_value)
                                
                                # Update the files label with percentage
                                files_label.configure(text=f"{completed_files}/{len(files_to_download)} files completed ({overall_percentage:.1f}%)")
                            
                            # Force an update of the dialog to ensure changes are visible
                            progress_dialog.update_idletasks()
                        
                        elif status == "complete":
                            file_name, component_type = data
                            completed_files += 1
                            
                            # Update file progress widget to show completion
                            if file_name in file_progress_widgets:
                                _, file_label, file_progress_bar = file_progress_widgets[file_name]
                                file_progress_bar.set(1.0)  # Set to 100%
                                file_label.configure(text=f"{file_name} ({component_type}) - Complete")
                            
                            # Update overall progress
                            files_label.configure(text=f"{completed_files}/{len(files_to_download)} files completed")
                            progress_bar.set(completed_files / len(files_to_download))
                            
                            # Force an update of the dialog to ensure changes are visible
                            progress_dialog.update_idletasks()
                        
                        elif status == "error":
                            file_name, component_type, error_message = data
                            
                            # Update file progress widget
                            if file_name in file_progress_widgets:
                                _, file_label, file_progress_bar = file_progress_widgets[file_name]
                                file_label.configure(text=f"{file_name} ({component_type}) - Error: {error_message}")
                            
                            # Add to download errors
                            download_errors.append(f"Error downloading {file_name} ({component_type}): {error_message}")
                            
                            # Force an update of the dialog to ensure changes are visible
                            progress_dialog.update_idletasks()
                    except Exception as e:
                        print(f"Error processing download queue: {e}")
                
                # Check if all downloads are complete
                if completed_files >= len(files_to_download):
                    # All downloads complete, close dialog if it's still open
                    if not dialog_closed[0]:
                        dialog_closed[0] = True
                        try:
                            progress_dialog.destroy()
                        except:
                            pass
                        
                        # Show success or error message
                        if download_errors:
                            error_message = "\n".join(download_errors)
                            self._show_error(f"Some files failed to download:\n{error_message}")
                        else:
                            self._show_success("All files downloaded successfully")
                else:
                    # Schedule the next queue processing
                    if parent and not downloads_cancelled[0]:
                        parent.after(100, process_download_queue)
            
            # Define dialog close handler
            def on_dialog_close():
                # Show confirmation dialog asking if user wants to interrupt the download
                try:
                    import tkinter.messagebox as messagebox
                    if messagebox.askyesno("Interrupt Download", "The download will be interrupted if you close this window. Do you want to continue?"):
                        # User confirmed they want to cancel the download
                        cancel_downloads()
                    else:
                        # User chose to continue downloading, don't close the dialog
                        return
                except Exception as e:
                    print(f"Error showing confirmation dialog: {e}")
                    # If there's an error showing the dialog, default to cancelling
                    cancel_downloads()
                
                return True  # Return True to allow the window to close
            
            # Store the cancel flag
            progress_dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
            
            # Calculate total bytes if available
            for _, _, file_name, component_type in files_to_download:
                file_progress[file_name] = (0, 0)  # (downloaded, total)
            
            # Start processing the download queue in the main thread
            if parent:
                parent.after(100, process_download_queue)
            
            # Create a monitoring thread to check if all downloads are complete
            def monitor_downloads():
                while completed_files < len(files_to_download) and not downloads_cancelled[0]:
                    time.sleep(0.5)
                
                # If we're here, either all downloads are complete or they were cancelled
                if not downloads_cancelled[0] and not dialog_closed[0]:
                    # All downloads complete, close dialog
                    dialog_closed[0] = True
                    try:
                        parent.after_idle(progress_dialog.destroy)
                    except:
                        pass
                    
                    # Show success or error message
                    if download_errors:
                        error_message = "\n".join(download_errors)
                        parent.after_idle(lambda: self._show_error(f"Some files failed to download:\n{error_message}"))
                    else:
                        parent.after_idle(lambda: self._show_success("All files downloaded successfully"))
            
            # Start monitoring thread
            monitor_thread = threading.Thread(target=monitor_downloads)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Return immediately, downloads will continue in background
            return True, "Downloads started"
            
        except Exception as e:
            print(f"\nError in prepare_offline_package: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Failed to create offline package: {str(e)}" 

    def _ask_download_again(self, component_type, existing_files, parent=None):
        """
        Ask the user if they want to download files again when they already exist.
        
        Args:
            component_type (str): The type of component (e.g., "POS Java")
            existing_files (list): List of existing files
            parent: Parent window for the dialog
            
        Returns:
            bool: True if the user wants to download again, False otherwise
        """
        import customtkinter as ctk
        import tkinter as tk
        import sys
        
        # Use the parent if provided, otherwise use self.parent_window, or create a new root
        parent = parent or self.parent_window
        
        # Format the list of existing files
        files_str = "\n".join(existing_files)
        
        if parent:
            # Create a dialog
            result = [False]  # Use a list to store the result (to be modified by inner functions)
            
            dialog = ctk.CTkToplevel(parent)
            dialog.title(f"Existing {component_type} Files Found")
            dialog.geometry("600x450")
            dialog.transient(parent)
            
            # Force update to ensure dialog is properly created
            dialog.update_idletasks()
            
            # Linux-specific handling
            if sys.platform.startswith('linux'):
                dialog.attributes("-topmost", True)
                dialog.update()
                
            dialog.grab_set()
            dialog.focus_force()
            
            # Title
            ctk.CTkLabel(
                dialog,
                text=f"Existing {component_type} Files Found",
                font=("Helvetica", 16, "bold")
            ).pack(pady=(20, 10), padx=20)
            
            # Message
            ctk.CTkLabel(
                dialog,
                text=f"The following {component_type} files already exist:",
                font=("Helvetica", 12)
            ).pack(pady=(0, 10), padx=20)
            
            # Create a scrollable frame for the files list
            files_frame = ctk.CTkScrollableFrame(dialog, width=550, height=200)
            files_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Add files to the scrollable frame
            for file in existing_files:
                ctk.CTkLabel(
                    files_frame,
                    text=file,
                    font=("Helvetica", 11),
                    anchor="w"
                ).pack(fill="x", padx=5, pady=2, anchor="w")
            
            # Question
            ctk.CTkLabel(
                dialog,
                text="Do you want to download these files again?",
                font=("Helvetica", 12)
            ).pack(pady=(10, 20), padx=20)
            
            # Buttons
            button_frame = ctk.CTkFrame(dialog)
            button_frame.pack(fill="x", pady=(0, 20), padx=20)
            
            def on_yes():
                result[0] = True
                dialog.destroy()
                
            def on_no():
                result[0] = False
                dialog.destroy()
                
            ctk.CTkButton(
                button_frame,
                text="No, Skip Download",
                command=on_no,
                width=180,
                fg_color="#555555",
                hover_color="#333333"
            ).pack(side="left", padx=10)
            
            ctk.CTkButton(
                button_frame,
                text="Yes, Download Again",
                command=on_yes,
                width=180
            ).pack(side="right", padx=10)
            
            # One more update to ensure everything is displayed
            dialog.update_idletasks()
            
            # Wait for the dialog to close
            parent.wait_window(dialog)
            
            return result[0]
        else:
            # If no parent window, use console input
            print(f"\nExisting {component_type} files found:")
            for file in existing_files:
                print(f"  - {file}")
            
            while True:
                response = input(f"Do you want to download {component_type} files again? (y/n): ").lower()
                if response in ['y', 'yes']:
                    return True
                elif response in ['n', 'no']:
                    return False
                else:
                    print("Please enter 'y' or 'n'.")

    def _show_info(self, title, message):
        """Show an info message dialog."""
        if self.parent_window:
            import tkinter.messagebox as messagebox
            messagebox.showinfo(title, message)
        else:
            print(f"\n{title}: {message}")

    def _create_default_templates(self, launchers_dir):
        """Create default templates in the source directory"""
        self._create_default_template(launchers_dir, "launcher.pos.template")
        self._create_default_template(launchers_dir, "launcher.wdm.template")
        self._create_default_template(launchers_dir, "launcher.flow-service.template")
        self._create_default_template(launchers_dir, "launcher.lpa-service.template")
        self._create_default_template(launchers_dir, "launcher.storehub-service.template")

    def _create_default_template(self, launchers_dir, filename):
        """Create a default template in the source directory"""
        template_content = ""
        
        if filename == "launcher.pos.template":
            template_content = """# Launcher defaults for POS
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationJmxPort=
updaterJmxPort=
createShortcuts=0
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
hardware_package_local=
"""
        elif filename == "launcher.wdm.template":
            template_content = """# Launcher defaults for WDM
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8080
applicationServerHttpsPort=8443
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
        elif filename == "launcher.flow-service.template":
            template_content = """# Launcher defaults for Flow Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
        elif filename == "launcher.lpa-service.template":
            template_content = """# Launcher defaults for LPA Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
        elif filename == "launcher.storehub-service.template":
            template_content = """# Launcher defaults for StoreHub Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
applicationJmsPort=7001
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
firebirdServerPath=@FIREBIRD_SERVER_PATH@
firebird_driver_path_local=@FIREBIRD_DRIVER_PATH_LOCAL@
firebirdServerPort=3050
firebirdServerUser=SYSDBA
firebirdServerPassword=masterkey
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
        
        # Write the template to the file
        file_path = os.path.join(launchers_dir, filename)
        try:
            with open(file_path, 'w') as f:
                f.write(template_content)
            print(f"Created default template: {filename}")
        except Exception as e:
            print(f"Error creating default template {filename}: {str(e)}")

    def _replace_hostname_regex_powershell(self, template_content, custom_regex):
        """Replace the hostname detection regex in PowerShell template"""
        import re
        
        # The pattern to find in the PowerShell template
        # We're looking for the hostname detection section where the regex is used
        pattern = r'if \(\$hs -match "([^"]+)"\) \{[\s\n]+\s+\$storeId = \$matches\[1\][\s\n]+\s+\$workstationId = \$matches\[2\]'
        
        # Sanitize regex for PowerShell string
        # Need to escape any backslashes for PowerShell string
        sanitized_regex = custom_regex.replace('\\', '\\\\')
        
        # The replacement with our custom regex
        replacement = f'if ($hs -match "{sanitized_regex}") {{\n    $storeId = $matches[1]\n    $workstationId = $matches[2]'
        
        # Replace in the template
        modified_content = re.sub(pattern, replacement, template_content)
        
        # Also update the validation regex for workstation ID
        # Find the validation pattern
        ws_validation_pattern = r'\$workstationId -match \'\^\\\d\{3\}\$\''
        
        # Replace with more permissive pattern that accepts any digit length
        ws_validation_replacement = r'$workstationId -match \'^\\\d+$\''
        
        # Replace in the template
        modified_content = re.sub(ws_validation_pattern, ws_validation_replacement, modified_content)
        
        return modified_content
        
    def _replace_hostname_regex_bash(self, template_content, custom_regex):
        """Replace the hostname detection regex in Bash template"""
        import re
        
        # The pattern to find in the Bash template
        # We're looking for the hostname detection section where the regex is used
        pattern = r'if \[\[ "\$hs" =~ ([^\]]+) \]\]; then[\s\n]+\s+storeId="\$\{BASH_REMATCH\[1\]\}"[\s\n]+\s+workstationId="\$\{BASH_REMATCH\[2\]\}"'
        
        # Sanitize regex for Bash
        # Need to escape any backslashes and special chars for Bash
        sanitized_regex = custom_regex.replace('\\', '\\\\')
        
        # The replacement with our custom regex
        replacement = f'if [[ "$hs" =~ {sanitized_regex} ]]; then\n      storeId="${{BASH_REMATCH[1]}}"\n      workstationId="${{BASH_REMATCH[2]}}"'
        
        # Replace in the template
        modified_content = re.sub(pattern, replacement, template_content)
        
        # Also update the validation regex for workstation ID 
        # Find the validation pattern
        ws_validation_pattern = r'\[\[ "\$workstationId" =~ \^[0-9]{3}\$ \]\]'
        
        # Replace with more permissive pattern that accepts any digit length
        ws_validation_replacement = r'[[ "$workstationId" =~ ^[0-9]+$ ]]'
        
        # Replace in the template
        modified_content = re.sub(ws_validation_pattern, ws_validation_replacement, modified_content)
        
        return modified_content