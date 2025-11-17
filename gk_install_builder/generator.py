import os
import re
import json
import shutil
import customtkinter as ctk
import base64
import platform
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import time
import threading
import queue
from detection import DetectionManager
import re
from datetime import datetime
from urllib.parse import unquote
import requests
import logging
from string import Template
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor

# Support both package-relative imports (for tests/package use) and direct imports (for running app)
try:
    from .gen_config import TEMPLATE_DIR, HELPER_STRUCTURE, DEFAULT_DOWNLOAD_WORKERS, DEFAULT_CHUNK_SIZE, LAUNCHER_TEMPLATES
    from .utils import create_directory_structure, copy_certificate, write_installation_script, determine_gk_install_paths, replace_urls_in_json, create_helper_structure, setup_firebird_environment_variables, get_component_version
    from .generators import (
        replace_hostname_regex_powershell,
        replace_hostname_regex_bash,
        generate_launcher_templates,
        create_default_template,
        generate_onboarding_script,
        generate_store_init_script,
        create_password_files,
        create_component_files,
        create_init_json_files,
        modify_json_files,
        copy_helper_files,
        generate_environments_json,
        download_file_thread,
        create_progress_dialog,
        prompt_for_file_selection,
        process_platform_dependency,
        process_component
    )
except ImportError:
    # Fall back to direct imports when run from gk_install_builder directory
    from gen_config.generator_config import TEMPLATE_DIR, HELPER_STRUCTURE, DEFAULT_DOWNLOAD_WORKERS, DEFAULT_CHUNK_SIZE, LAUNCHER_TEMPLATES
    from utils.file_operations import create_directory_structure, copy_certificate, write_installation_script, determine_gk_install_paths
    from utils.helpers import replace_urls_in_json, create_helper_structure
    from utils.environment_setup import setup_firebird_environment_variables
    from utils.version import get_component_version
    from generators.template_processor import replace_hostname_regex_powershell, replace_hostname_regex_bash
    from generators.launcher_generator import generate_launcher_templates
    from generators.onboarding_generator import generate_onboarding_script
    from generators.helper_file_generator import (
        generate_store_init_script,
        create_password_files,
        create_component_files,
        create_init_json_files,
        modify_json_files,
        copy_helper_files,
        generate_environments_json
    )
    from generators.launcher_generator import create_default_template
    from generators.offline_package_helpers import (
        download_file_thread,
        create_progress_dialog,
        prompt_for_file_selection,
        process_platform_dependency,
        process_component
    )

# Disable insecure request warnings
urllib3.disable_warnings(InsecureRequestWarning)

class DSGRestBrowser:
    """Browser for DSG REST API (replaces WebDAV)"""
    def __init__(self, base_url, username=None, password=None, bearer_token=None):
        if not base_url.startswith('http'):
            base_url = f'https://{base_url}'
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.bearer_token = bearer_token
        self.connected = False
        self.current_path = "/SoftwarePackage"
        
        # Token refresh callback - set by parent to handle token regeneration
        self.token_refresh_callback = None
        
        # REST API endpoint
        self.api_base = f"{self.base_url}/api/digital-content/services/rest/media/v1/files"
        
        print("\nDSG REST API Client:")
        print(f"Base URL: {self.base_url}")
        print(f"API Endpoint: {self.api_base}")
        print(f"Username: {self.username}")

    def _normalize_path(self, path):
        """Normalize path for REST API"""
        path = path.replace('\\', '/')
        path = path.strip('/')
        return '/' + path if path else '/'

    def _get_headers(self):
        """Get headers for REST API requests"""
        headers = {
            'Accept': 'application/json; variant=Plain; charset=UTF-8',
            'Content-Type': 'application/json; variant=Plain; charset=UTF-8',
            'GK-Accept-Redirect': '308',
            'Connection': 'keep-alive'
        }
        
        if self.bearer_token:
            headers['Authorization'] = f'Bearer {self.bearer_token}'
        
        return headers

    def _handle_api_request(self, request_func, retry_on_401=True):
        """Handle API requests with automatic token refresh on 401"""
        try:
            response = request_func()
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401 and retry_on_401 and self.token_refresh_callback:
                print("\n=== Token Expired (401) - Refreshing ===")
                print(f"Old token (last 10 chars): ...{self.bearer_token[-10:] if self.bearer_token else 'None'}")
                
                # Try to refresh the token
                new_token = self.token_refresh_callback()
                if new_token:
                    self.bearer_token = new_token
                    print(f"New token (last 10 chars): ...{self.bearer_token[-10:]}")
                    print("Token updated successfully, retrying request with new token...")
                    
                    # Retry the request once with new token (headers will be regenerated)
                    response = request_func()
                    response.raise_for_status()
                    print("Request succeeded with new token!")
                    return response
                else:
                    print("Token refresh failed - no new token returned")
            raise
    
    def list_directories(self, path="/SoftwarePackage"):
        """List files and directories using REST API with auto token refresh"""
        try:
            # Check if connected
            if not self.connected:
                print("Warning: Not connected to REST API")
                return []
                
            # Normalize path
            path = self._normalize_path(path)
            print(f"Listing directory via REST API: {path}")
            
            # Build API URL - remove leading slash for API path
            api_path = path.lstrip('/')
            url = f"{self.api_base}/{api_path}"
            
            # Add query parameters
            params = {
                'metadata': 'true',
                'offset': 0,
                'limit': 1000  # Get more items than the default 25
            }
            
            print(f"Request URL: {url}")
            print(f"Request params: {params}")
            
            # Define the request function for retry logic
            def make_request():
                return requests.get(
                    url,
                    headers=self._get_headers(),
                    params=params,
                    verify=False
                )
            
            # Make request with automatic token refresh on 401
            response = self._handle_api_request(make_request)
            data = response.json()
            
            print(f"Response status: {response.status_code}")
            print(f"Found {len(data.get('resources', []))} resources")
            
            items = []
            for resource in data.get('resources', []):
                name = resource.get('name', '')
                resource_type = resource.get('type', '')
                
                # type="collection" means directory, type="resource" means file
                is_directory = resource_type == 'collection'
                
                item = {
                    'name': name,
                    'is_directory': is_directory,
                    'path': resource.get('path', ''),
                    'size': resource.get('size'),
                    'mimeType': resource.get('mimeType'),
                    'lastModification': resource.get('lastModification')
                }
                items.append(item)
            
            return items
            
        except requests.exceptions.RequestException as e:
            print(f"Error listing directory via REST API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            return []
        except Exception as e:
            print(f"Unexpected error listing directory: {str(e)}")
            return []

    def connect(self):
        """Test REST API connection"""
        try:
            print("Testing REST API connection with:")
            print(f"URL: {self.api_base}")
            print(f"Username: {self.username}")
            
            # Try to list the root SoftwarePackage directory
            url = f"{self.api_base}/SoftwarePackage"
            params = {'metadata': 'true', 'offset': 0, 'limit': 1}
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                verify=False
            )
            
            response.raise_for_status()
            data = response.json()
            
            print(f"Connection successful. Found {len(data.get('resources', []))} items")
            self.connected = True
            return True, "Connected successfully"
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Connection failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" (Status: {e.response.status_code})"
            print(error_msg)
            self.connected = False
            return False, error_msg
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            print(error_msg)
            self.connected = False
            return False, error_msg

    def list_directory(self, path="/SoftwarePackage"):
        """Alias for list_directories"""
        return self.list_directories(path)

    def get_file_url(self, file_path):
        """Get the download URL for a file using /dsg/content/cep/ path"""
        # Remove leading slash and 'SoftwarePackage/' prefix if present
        file_path = file_path.lstrip('/')
        if file_path.startswith('SoftwarePackage/'):
            file_path = file_path[len('SoftwarePackage/'):]
        
        # Use /dsg/content/cep/ path for actual file downloads
        return f"{self.base_url}/dsg/content/cep/SoftwarePackage/{file_path}"

# Keep WebDAVBrowser as an alias for backwards compatibility during transition
WebDAVBrowser = DSGRestBrowser

class ProjectGenerator:
    def __init__(self, parent_window=None):
        self.template_dir = TEMPLATE_DIR
        self.helper_structure = HELPER_STRUCTURE
        self.dsg_api_browser = None
        self.parent_window = parent_window  # Rename to parent_window for consistency
        self.detection_manager = DetectionManager()

        # Enable file detection by default
        self.detection_manager.enable_file_detection(True)

        # Download concurrency and networking tuning
        self.max_download_workers = DEFAULT_DOWNLOAD_WORKERS
        self.download_chunk_size = DEFAULT_CHUNK_SIZE
        self._session_local = threading.local()
        self._http_adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=frozenset(["GET"]) 
            ),
        )

    def create_dsg_api_browser(self, base_url, username=None, password=None, bearer_token=None):
        """Create a new DSG REST API browser instance"""
        self.dsg_api_browser = DSGRestBrowser(base_url, username, password, bearer_token)
        return self.dsg_api_browser

    def _get_session(self):
        """Get a per-thread requests Session with tuned connection pool and retries."""
        if not hasattr(self._session_local, 'session'):
            s = requests.Session()
            s.mount('https://', self._http_adapter)
            s.mount('http://', self._http_adapter)
            self._session_local.session = s
        return self._session_local.session

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
            
            # Generate environments.json if environments are configured
            self._generate_environments_json(output_dir, config)
            
            self._show_success(f"Project generated in: {output_dir}")
        except Exception as e:
            self._show_error(f"Failed to generate project: {str(e)}")
            # Print detailed error for debugging
            import traceback
            print(f"Error details: {traceback.format_exc()}")

    def _create_directory_structure(self, output_dir):
        """Create the project directory structure"""
        create_directory_structure(output_dir, self.helper_structure)

    def _copy_certificate(self, output_dir, config):
        """Copy SSL certificate to output directory if it exists"""
        return copy_certificate(output_dir, config)
    
    def _generate_environments_json(self, output_dir, config):
        """Generate environments.json file for multi-environment support"""
        return generate_environments_json(output_dir, config)

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
            
            # Set environment variables for Firebird
            setup_firebird_environment_variables(config, platform)

            # Determine template and output paths based on platform
            template_path, output_path, template_filename, output_filename = determine_gk_install_paths(
                platform, output_dir, os.path.dirname(os.path.abspath(__file__))
            )

            print(f"Generating {output_filename}:")
            print(f"  Template path: {template_path}")
            print(f"  Output path: {output_path}")
            print(f"  Use hostname detection: {use_hostname_detection}")
            
            # Check if template exists
            if not os.path.exists(template_path):
                raise Exception(f"Template file not found: {template_path}")
            
            with open(template_path, 'r') as f:
                template = f.read()
                
            # Apply custom regex if available and hostname detection is enabled
            if use_hostname_detection and "detection_config" in config and "hostname_detection" in config["detection_config"]:
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
            
            # Handle hostname environment detection
            hostname_env_detection = self.detection_manager.get_hostname_env_detection()
            print(f"  Hostname environment detection: {hostname_env_detection}")
            
            # Only enable environment detection if both hostname detection is enabled AND env detection is enabled
            if use_hostname_detection and hostname_env_detection:
                # Get configured group mappings
                group_mappings = self.detection_manager.get_all_group_mappings()
                env_group = group_mappings.get("env", 1)
                store_group = group_mappings.get("store", 2)
                ws_group = group_mappings.get("workstation", 3)
                
                # Insert hostname environment detection code
                if platform == "Windows":
                    # Get the configured regex pattern for hostname detection
                    hostname_regex = self.detection_manager.get_hostname_regex("windows")
                    
                    hostname_env_code = f'''# Priority 2: Hostname environment detection
    Write-Host "[2] Hostname Detection: Extracting environment from hostname..."
    try {{
        $hostname = $env:COMPUTERNAME
        Write-Host "    Computer name: $hostname"
        
        # Use the configured hostname regex to extract environment (group {env_group}), store (group {store_group}), and workstation (group {ws_group})
        # Regex pattern: {hostname_regex}
        if ($hostname -match '{hostname_regex}') {{
            if ($matches.Count -ge 4) {{
                # 3-group regex: Environment, Store, Workstation
                $hostnameEnv = $matches[{env_group}]
                Write-Host "    Extracted environment from hostname: $hostnameEnv"
                $selectedEnv = $environments | Where-Object {{ $_.alias -eq $hostnameEnv }} | Select-Object -First 1
                if ($selectedEnv) {{
                    Write-Host "    [OK] Matched: $($selectedEnv.name) ($($selectedEnv.base_url))"
                    return $selectedEnv
                }} else {{
                    Write-Host "    [X] ERROR: Environment '$hostnameEnv' detected from hostname but not configured!"
                    Write-Host ""
                    Show-Environments
                    Write-Host ""
                    Write-Host "Please add environment '$hostnameEnv' to your configuration."
                    exit 1
                }}
            }} else {{
                Write-Host "    [X] Regex matched but does not have 3 capture groups (need: Environment, Store, Workstation)"
            }}
        }} else {{
            Write-Host "    Hostname does not match the configured pattern"
        }}
    }} catch {{
        Write-Host "    [X] Error during hostname detection: $_"
    }}
    
    # Priority 3: Environment file detection from .station files
    Write-Host "[3] File Detection: Checking for environment in .station file..."
    '''
                    # Replace the placeholder and update priority numbers
                    template = template.replace("# HOSTNAME_ENV_DETECTION_PLACEHOLDER\n    \n    # Priority 2:", hostname_env_code + "\n    # Priority 3:")
                    # Also update the interactive prompt priority to 4
                    template = template.replace("# Priority 3: Interactive prompt\n    Write-Host \"[3] Interactive Selection:", "# Priority 4: Interactive prompt\n    Write-Host \"[4] Interactive Selection:")
                else:  # Linux
                    # Get the configured regex pattern for hostname detection
                    hostname_regex = self.detection_manager.get_hostname_regex("linux")
                    
                    hostname_env_code = f'''# Priority 2: Hostname environment detection
  echo "[2] Hostname Detection: Extracting environment from hostname..." >&2
  
  local hostname=$(hostname)
  echo "    Computer name: $hostname" >&2
  
  # Use the configured hostname regex to extract environment (group {env_group}), store (group {store_group}), and workstation (group {ws_group})
  # Regex pattern: {hostname_regex}
  if [[ "$hostname" =~ {hostname_regex} ]]; then
    if [ ${{#BASH_REMATCH[@]}} -ge 4 ]; then
      # 3-group regex: Environment, Store, Workstation
      local hostname_env="${{BASH_REMATCH[{env_group}]}}"
      echo "    Extracted environment from hostname: $hostname_env" >&2
      local selected=$(echo "$environments" | jq --arg alias "$hostname_env" '.environments[] | select(.alias == $alias)')
      if [ -n "$selected" ]; then
        echo "    ✓ Matched environment" >&2
        echo "$selected"
        return 0
      else
        echo "    ✗ ERROR: Environment '$hostname_env' detected from hostname but not configured!" >&2
        echo "" >&2
        show_environments
        echo "" >&2
        echo "Please add environment '$hostname_env' to your configuration." >&2
        exit 1
      fi
    else
      echo "    ✗ Regex matched but does not have 3 capture groups (need: Environment, Store, Workstation)" >&2
    fi
  else
    echo "    Hostname does not match the configured pattern" >&2
  fi
  
  # Priority 3: File detection from .station files
  echo "[3] File Detection: Checking for environment in .station file..." >&2
  '''
                    # Replace the placeholder and update priority numbers
                    template = template.replace("# HOSTNAME_ENV_DETECTION_PLACEHOLDER\n  \n  # Priority 2:", hostname_env_code + "\n  # Priority 3:")
                    # Also update the interactive prompt priority to 4
                    template = template.replace("# Priority 3: Interactive prompt", "# Priority 4: Interactive prompt")
            else:
                # Remove the placeholder when disabled
                template = template.replace("# HOSTNAME_ENV_DETECTION_PLACEHOLDER\n    \n    ", "")
                template = template.replace("# HOSTNAME_ENV_DETECTION_PLACEHOLDER\n  \n  ", "")
            
            # Replace hostname Store/Workstation detection with appropriate code
            if platform == "Windows":
                hostname_regex = self.detection_manager.get_hostname_regex("windows")
                
                # Get configured group mappings
                group_mappings = self.detection_manager.get_all_group_mappings()
                env_group = group_mappings.get("env", 1)
                store_group = group_mappings.get("store", 2)
                ws_group = group_mappings.get("workstation", 3)
                
                if hostname_env_detection:
                    # 3-group pattern: Use configured group mappings
                    store_workstation_code = rf'''if ($hs -match '{hostname_regex}') {{
            # 3-group pattern: Environment ({env_group}), Store ID ({store_group}), Workstation ID ({ws_group})
            $storeId = $matches[{store_group}]
            $workstationId = $matches[{ws_group}]
            $storeNumber = $storeId

            # Validate extracted parts
            if ($storeNumber -match '^[A-Za-z0-9_.-]+$') {{
                if ($workstationId -match '^[0-9]+$') {{
                    $hostnameDetected = $true
                    Write-Host "Successfully detected values from hostname:"
                    Write-Host "Store Number: $storeNumber"
                    Write-Host "Workstation ID: $workstationId"
                }}
            }}
        }}'''
                else:
                    # 2-group pattern: Use configured group mappings (store and workstation only)
                    store_workstation_code = rf'''if ($hs -match '{hostname_regex}') {{
            # Pattern like R005-101 or SOMENAME-1674-101 where last part is digits
            $storeId = $matches[{store_group}]
            $workstationId = $matches[{ws_group}]

            # If storeId contains a dash, it might be SOMENAME-1674-101 format
            if ($storeId -match '.*-(\d{{4}})$') {{
                $storeNumber = $matches[1]
            }} else {{
                # Direct format like R005-101
                $storeNumber = $storeId
            }}

            # Validate extracted parts
            if ($storeNumber -match '^[A-Za-z0-9_.-]+$') {{
                if ($workstationId -match '^[0-9]+$') {{
                    $hostnameDetected = $true
                    Write-Host "Successfully detected values from hostname:"
                    Write-Host "Store Number: $storeNumber"
                    Write-Host "Workstation ID: $workstationId"
                }}
            }}
        }}'''
                
                # Replace the placeholder
                template = template.replace("# HOSTNAME_STORE_WORKSTATION_DETECTION_PLACEHOLDER", store_workstation_code)
            else:  # Linux
                hostname_regex = self.detection_manager.get_hostname_regex("linux")
                
                # Get configured group mappings
                group_mappings = self.detection_manager.get_all_group_mappings()
                env_group = group_mappings.get("env", 1)
                store_group = group_mappings.get("store", 2)
                ws_group = group_mappings.get("workstation", 3)
                
                if hostname_env_detection:
                    # 3-group pattern: Use configured group mappings
                    store_workstation_code = f'''# Extract the last part (workstation ID)
    if [[ "$hs" =~ {hostname_regex} ]]; then
      # 3-group pattern: Environment ({env_group}), Store ID ({store_group}), Workstation ID ({ws_group})
      storeNumber="${{BASH_REMATCH[{store_group}]}}"
      workstationId="${{BASH_REMATCH[{ws_group}]}}"
      
      # Validate extracted parts
      # Accept any alphanumeric characters for store ID with at least 1 character
      if echo "$storeNumber" | grep -qE '^[A-Za-z0-9_\\-\\.]+$'; then
        if [[ "$workstationId" =~ ^[0-9]+$ ]]; then
          hostnameDetected=true
          echo "Successfully detected values from hostname:"
          echo "Store Number: $storeNumber"
          echo "Workstation ID: $workstationId"
        fi
      fi
    fi'''
                else:
                    # 2-group pattern: Use configured group mappings (store and workstation only)
                    store_workstation_code = f'''# Extract the last part (workstation ID)
    if [[ "$hs" =~ {hostname_regex} ]]; then
      storeId="${{BASH_REMATCH[{store_group}]}}"
      workstationId="${{BASH_REMATCH[{ws_group}]}}"
      
      # If storeId contains a dash, it might be SOMENAME-1674-101 format
      if [[ "$storeId" =~ .*-([0-9]{{4}})$ ]]; then
        storeNumber="${{BASH_REMATCH[1]}}"
      else
        # Direct format like R005-101
        storeNumber="$storeId"
      fi
      
      # Validate extracted parts
      # Accept any alphanumeric characters for store ID with at least 1 character
      if echo "$storeNumber" | grep -qE '^[A-Za-z0-9_\\-\\.]+$'; then
        if [[ "$workstationId" =~ ^[0-9]+$ ]]; then
          hostnameDetected=true
          echo "Successfully detected values from hostname:"
          echo "Store Number: $storeNumber"
          echo "Workstation ID: $workstationId"
        fi
      fi
    fi'''
                
                # Replace the hardcoded detection logic in the bash template
                # Find and replace the block between "# Try different patterns:" and "# If hostname detection failed"
                import re
                bash_detection_pattern = r'(# Try different patterns:.*?)(# Extract the last part \(workstation ID\).*?fi\s+fi\s+fi)'
                template = re.sub(bash_detection_pattern, 
                                  r'\1' + store_workstation_code,
                                  template, flags=re.DOTALL)
            
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
            
            # Get version source setting
            version_source = config.get("default_version_source", "FP")
            # Map CONFIG-SERVICE (GUI display name) to CONFIG (script value)
            if version_source == "CONFIG-SERVICE":
                version_source = "CONFIG"
            
            # Get form username (eh_launchpad_username)
            form_username = config.get("eh_launchpad_username", "1001")
            
            if platform == "Windows":
                    # Windows-specific replacements
                    replacements = [
                        ("test.cse.cloud4retail.co", base_url),
                        ("C:\\gkretail", base_install_dir.replace("\\", "\\\\")),  # double backslash
                        ("C:/gkretail", base_install_dir.replace("\\", "/")),  # handle any accidental forward slashes
                        (r"C:\gkretail", base_install_dir),  # single backslash (main fix)
                        ("$base_install_dir = \"C:\\gkretail\"", f"$base_install_dir = \"{base_install_dir}\""),  # assignment line
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
                        ("@USE_DEFAULT_VERSIONS@", "$true" if config.get("use_default_versions", False) else "$false"),
                        ("@VERSION_SOURCE@", version_source),
                        ("@FORM_USERNAME@", form_username),
                        ("@POS_SYSTEM_TYPE@", pos_system_type),
                        ("@WDM_SYSTEM_TYPE@", wdm_system_type),
                        ("@FLOW_SERVICE_SYSTEM_TYPE@", flow_service_system_type),
                        ("@LPA_SERVICE_SYSTEM_TYPE@", lpa_service_system_type),
                        ("@STOREHUB_SERVICE_SYSTEM_TYPE@", storehub_service_system_type),
                        ("@TENANT_ID@", tenant_id)
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
                    ("@USE_DEFAULT_VERSIONS@", "true" if config.get("use_default_versions", False) else "false"),
                    ("@VERSION_SOURCE@", version_source),
                    ("@FORM_USERNAME@", form_username),
                    ("@POS_SYSTEM_TYPE@", pos_system_type),
                    ("@WDM_SYSTEM_TYPE@", wdm_system_type),
                    ("@FLOW_SERVICE_SYSTEM_TYPE@", flow_service_system_type),
                    ("@LPA_SERVICE_SYSTEM_TYPE@", lpa_service_system_type),
                    ("@STOREHUB_SERVICE_SYSTEM_TYPE@", storehub_service_system_type),
                    ("@TENANT_ID@", tenant_id)
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
            # Instead of completely different code paths, we'll use a pattern that never matches
            # when hostname detection is disabled, ensuring consistent credential setup
            if not use_hostname_detection:
                print("Hostname detection disabled - using never-match pattern to ensure consistent structure")
                # Use a regex pattern that will never match any real hostname
                never_match_pattern = "^NEVER_MATCH_THIS_HOSTNAME_PATTERN$"

                if platform == "Windows":
                    # Replace the hostname detection regex with a never-match pattern and add informative message
                    template = self._replace_hostname_regex_powershell(template, never_match_pattern, add_disabled_message=True)
                else:
                    # Replace the hostname detection regex with a never-match pattern and add informative message
                    template = self._replace_hostname_regex_bash(template, never_match_pattern, add_disabled_message=True)

            
            # Apply file detection settings - always insert code but use never-match pattern when disabled
            file_detection_enabled = self.detection_manager.is_detection_enabled()
            
            # Replace FILE_DETECTION_ENABLED placeholder
            template = template.replace("@FILE_DETECTION_ENABLED@", "True" if file_detection_enabled else "False")

            # Always insert file detection code for consistent structure
            # Use never-match pattern when file detection is disabled
            if platform == "Windows":
                # Always generate file detection code, but use never-match pattern when disabled
                # This ensures consistent script structure regardless of detection settings
                if file_detection_enabled:
                    file_enabled_flag = "$true"
                    never_match_comment = ""
                    file_detection_message = ""
                else:
                    file_enabled_flag = "$true"  # Keep true but use never-match paths
                    never_match_comment = "# File detection disabled - using never-match pattern for consistent structure\n"
                    file_detection_message = 'Write-Host "File detection is disabled in configuration - skipping file detection" -ForegroundColor Yellow\n'

                station_detection_code = '''
        {never_match_comment}# File detection for the current component ($ComponentType)
        $fileDetectionEnabled = {file_enabled_flag}
        $componentType = $ComponentType

        # Check if we're using base directory or custom paths
        $useBaseDirectory = "{is_using_base_dir}".ToLower()

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
                $stationFilePath = "C:\\gkretail\\stations\\$componentType.station"
            }}
        }}

        # Check if file detection is enabled
        if ($fileDetectionEnabled) {{
            {file_detection_message}Write-Host "Trying file detection for $componentType using $stationFilePath"
            
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
                    if ($storeNumber -and $workstationId -match '^[0-9]+$') {{
                        $hostnameDetected = $true
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
    never_match_comment=never_match_comment,
    file_enabled_flag=file_enabled_flag,
    file_detection_message=file_detection_message,
    is_using_base_dir=str(self.detection_manager.is_using_base_directory()).lower(),
    base_dir=self.detection_manager.get_base_directory().replace('\\', '\\\\') if file_detection_enabled else "NEVER_MATCH_BASE_DIR",
    pos_filename=self.detection_manager.get_custom_filename("POS") if file_detection_enabled else r"NEVER_MATCH.station",
    wdm_filename=self.detection_manager.get_custom_filename("WDM") if file_detection_enabled else r"NEVER_MATCH.station",
    flow_filename=self.detection_manager.get_custom_filename("FLOW-SERVICE") if file_detection_enabled else r"NEVER_MATCH.station",
    lpa_filename=self.detection_manager.get_custom_filename("LPA-SERVICE") if file_detection_enabled else r"NEVER_MATCH.station",
    sh_filename=self.detection_manager.get_custom_filename("STOREHUB-SERVICE") if file_detection_enabled else r"NEVER_MATCH.station",
    pos_path=self.detection_manager.detection_config["detection_files"]["POS"].replace('\\', '\\\\') if file_detection_enabled else "NEVER_MATCH_FILE_PATH",
    wdm_path=self.detection_manager.detection_config["detection_files"]["WDM"].replace('\\', '\\\\') if file_detection_enabled else "NEVER_MATCH_FILE_PATH",
    flow_path=self.detection_manager.detection_config["detection_files"]["FLOW-SERVICE"].replace('\\', '\\\\') if file_detection_enabled else "NEVER_MATCH_FILE_PATH",
    lpa_path=self.detection_manager.detection_config["detection_files"]["LPA-SERVICE"].replace('\\', '\\\\') if file_detection_enabled else "NEVER_MATCH_FILE_PATH",
    sh_path=self.detection_manager.detection_config["detection_files"]["STOREHUB-SERVICE"].replace('\\', '\\\\') if file_detection_enabled else "NEVER_MATCH_FILE_PATH"
)

                # Find where to insert the file detection code
                # Try multiple possible markers to ensure we find the insertion point
                possible_markers = [
                    "# File detection code will be inserted here by the generator",
                    "# File detection will be inserted here by the generator",
                    "        # File detection code will be inserted here by the generator"
                ]

                insert_marker = None
                insert_pos = -1

                for marker in possible_markers:
                    insert_pos = template.find(marker)
                    if insert_pos != -1:
                        insert_marker = marker
                        print(f"Found insertion marker: '{marker}' at position {insert_pos}")
                        break

                # Use the found insertion point
                if insert_pos != -1 and insert_marker is not None:
                    # Always insert the detection code for consistent structure
                    # When disabled, it uses never-match patterns so will always fall through to manual input
                    template = template[:insert_pos] + station_detection_code + template[insert_pos + len(insert_marker):]
                    if file_detection_enabled:
                        print(f"Added dynamic station detection code to PowerShell script")
                    else:
                        print(f"Added station detection code with never-match pattern to PowerShell script (file detection disabled)")
                else:
                    print(f"Warning: Could not find insertion point for station detection code in PowerShell script")
            
            # For Linux, always insert file detection code for consistent structure
            # Use never-match pattern when file detection is disabled
            if platform == "Linux":
                # Always generate file detection code, but use never-match pattern when disabled
                if file_detection_enabled:
                    never_match_comment = ""
                    file_detection_message = ""
                else:
                    never_match_comment = "# File detection disabled - using never-match pattern for consistent structure\n"
                    file_detection_message = 'echo "File detection is disabled in configuration - skipping file detection"\n'

                station_detection_code = '''
{never_match_comment}# File detection for the current component ($COMPONENT_TYPE)
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
    {file_detection_message}echo "Trying file detection for $componentType using $stationFilePath"
    
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
    never_match_comment=never_match_comment,
    file_detection_message=file_detection_message,
    is_using_base_dir=str(self.detection_manager.is_using_base_directory()),
    base_dir=self.detection_manager.get_base_directory() if file_detection_enabled else "NEVER_MATCH_BASE_DIR",
    pos_filename=self.detection_manager.get_custom_filename("POS") if file_detection_enabled else r"NEVER_MATCH.station",
    wdm_filename=self.detection_manager.get_custom_filename("WDM") if file_detection_enabled else r"NEVER_MATCH.station",
    flow_filename=self.detection_manager.get_custom_filename("FLOW-SERVICE") if file_detection_enabled else r"NEVER_MATCH.station",
    lpa_filename=self.detection_manager.get_custom_filename("LPA-SERVICE") if file_detection_enabled else r"NEVER_MATCH.station",
    sh_filename=self.detection_manager.get_custom_filename("STOREHUB-SERVICE") if file_detection_enabled else r"NEVER_MATCH.station",
    pos_path=self.detection_manager.detection_config["detection_files"]["POS"] if file_detection_enabled else "NEVER_MATCH_FILE_PATH",
    wdm_path=self.detection_manager.detection_config["detection_files"]["WDM"] if file_detection_enabled else "NEVER_MATCH_FILE_PATH",
    flow_path=self.detection_manager.detection_config["detection_files"]["FLOW-SERVICE"] if file_detection_enabled else "NEVER_MATCH_FILE_PATH",
    lpa_path=self.detection_manager.detection_config["detection_files"]["LPA-SERVICE"] if file_detection_enabled else "NEVER_MATCH_FILE_PATH",
    sh_path=self.detection_manager.detection_config["detection_files"]["STOREHUB-SERVICE"] if file_detection_enabled else "NEVER_MATCH_FILE_PATH"
)
                
                # Find where to insert the file detection code
                insert_marker = "# File detection code will be inserted here by the generator"
                
                # Find the position to insert the code
                insert_pos = template.find(insert_marker)
                if insert_pos == -1:
                    # Try the alternative marker if the primary one isn't found
                    insert_marker = "# File detection will be inserted here by the generator"
                    insert_pos = template.find(insert_marker)
                
                if insert_pos != -1:
                    # Always insert the detection code for consistent structure
                    # When disabled, it uses never-match patterns so will always fall through to manual input
                    template = template[:insert_pos] + station_detection_code + template[insert_pos + len(insert_marker):]
                    if file_detection_enabled:
                        print(f"Added dynamic station detection code to Bash script")
                    else:
                        print(f"Added station detection code with never-match pattern to Bash script (file detection disabled)")
                else:
                    print(f"Warning: Could not find insertion point for station detection code in Bash script")
            
            # Write the installation script with platform-specific formatting
            write_installation_script(output_path, template, platform, output_filename)
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error generating installation script: {error_details}")
            raise Exception(f"Failed to generate installation script: {str(e)}")

    def _generate_launcher_templates(self, launchers_dir, config):
        """Generate launcher templates with custom settings from config"""
        generate_launcher_templates(launchers_dir, config, LAUNCHER_TEMPLATES)

    def _generate_onboarding(self, output_dir, config):
        """Generate onboarding script with replaced values based on platform"""
        templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
        generate_onboarding_script(output_dir, config, templates_dir)

    def _copy_helper_files(self, output_dir, config):
        """Copy helper files to output directory"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return copy_helper_files(output_dir, config, script_dir, self.helper_structure, LAUNCHER_TEMPLATES)

    def _create_helper_structure(self, helper_dir):
        """Create the necessary helper directory structure with placeholder files"""
        create_helper_structure(helper_dir, self.helper_structure, self._create_component_files)

    def _create_component_files(self, helper_dir):
        """Create component-specific directories and files"""
        create_component_files(helper_dir)

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
        create_init_json_files(helper_dir, config)

    def _create_password_files(self, helper_dir, config):
        """Create password files for onboarding"""
        create_password_files(helper_dir, config)

    def _modify_json_files(self, helper_dir, config):
        """Modify JSON files with new configuration"""
        modify_json_files(helper_dir, config, replace_urls_in_json)

    def _replace_urls_in_json(self, data, new_base_url):
        """Recursively replace URLs in JSON structure"""
        replace_urls_in_json(data, new_base_url)

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
        from .dialogs import ask_download_dependencies_only
        return ask_download_dependencies_only(component_type, parent or self.parent_window, error_message)

    def get_component_version(self, system_type, config):
        """Determine the correct version for a component based on its system type"""
        return get_component_version(system_type, config)

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

            # Allow config to tune concurrency and chunk size
            try:
                self.max_download_workers = int(config.get("download_workers", self.max_download_workers))
            except Exception:
                pass
            try:
                self.download_chunk_size = int(config.get("download_chunk_size", self.download_chunk_size))
            except Exception:
                pass
            print(f"Download workers: {self.max_download_workers}")
            print(f"Download chunk size: {self.download_chunk_size} bytes")
            
            # Initialize DSG REST API browser if not already initialized
            if not self.dsg_api_browser:
                print("\nInitializing DSG REST API browser...")
                self.dsg_api_browser = self.create_dsg_api_browser(
                    config["base_url"],
                    config.get("dsg_api_username"),
                    config.get("dsg_api_password"),
                    config.get("bearer_token")  # Add bearer token support
                )
                success, message = self.dsg_api_browser.connect()
                if not success:
                    raise Exception(f"Failed to connect to DSG REST API: {message}")
                print("DSG REST API connection successful")
            
            # Create a queue for download results
            download_queue = queue.Queue()
            downloaded_files = []
            download_errors = []
            # Collect all files to download first
            files_to_download = []
            
            # Process platform dependencies
            process_platform_dependency(
                "Java", "JAVA", "/SoftwarePackage/Java", "zip",
                platform_dependencies, self.dsg_api_browser,
                self._ask_download_again, dialog_parent,
                output_dir, files_to_download, download_errors,
                prompt_for_file_selection, config
            )
            process_platform_dependency(
                "Tomcat", "TOMCAT", "/SoftwarePackage/Tomcat", "zip",
                platform_dependencies, self.dsg_api_browser,
                self._ask_download_again, dialog_parent,
                output_dir, files_to_download, download_errors,
                prompt_for_file_selection, config
            )
            process_platform_dependency(
                "Jaybird", "JAYBIRD", "/SoftwarePackage/Drivers", "jar",
                platform_dependencies, self.dsg_api_browser,
                self._ask_download_again, dialog_parent,
                output_dir, files_to_download, download_errors,
                prompt_for_file_selection, config,
                file_filter=lambda files: [f for f in files if f.get('name', '').endswith('.jar')]
            )
            
            # Process application components
            process_component(
                "POS", "POS", "pos", "CSE-OPOS-CLOUD",
                selected_components, output_dir, config, self.get_component_version,
                self.dsg_api_browser, prompt_for_file_selection,
                files_to_download
            )
            process_component(
                "WDM", "WDM", "wdm", "CSE-wdm",
                selected_components, output_dir, config, self.get_component_version,
                self.dsg_api_browser, prompt_for_file_selection,
                files_to_download
            )
            process_component(
                "FLOW-SERVICE", "FLOW-SERVICE", "flow_service", "GKR-FLOWSERVICE-CLOUD",
                selected_components, output_dir, config, self.get_component_version,
                self.dsg_api_browser, prompt_for_file_selection,
                files_to_download,
                display_name="Flow Service"
            )
            process_component(
                "LPA", "LPA-SERVICE", "lpa_service", "CSE-lps-lpa",
                selected_components, output_dir, config, self.get_component_version,
                self.dsg_api_browser, prompt_for_file_selection,
                files_to_download,
                display_name="LPA Service"
            )
            process_component(
                "SH", "STOREHUB-SERVICE", "storehub_service", "CSE-sh-cloud",
                selected_components, output_dir, config, self.get_component_version,
                self.dsg_api_browser, prompt_for_file_selection,
                files_to_download,
                display_name="StoreHub Service"
            )
            
            # If no files to download, return
            if not files_to_download:
                return False, "No files were selected for download"
            
            # Create progress dialog
            parent = dialog_parent or self.parent_window
            if parent:
                progress_dialog, progress_bar, files_label, files_frame, file_progress_widgets, _ = create_progress_dialog(parent, len(files_to_download))
            
            # Concurrency limiter to cap simultaneous downloads
            concurrency_limiter = threading.BoundedSemaphore(self.max_download_workers)

            # Start download threads
            download_threads = []
            for remote_path, local_path, file_name, component_type in files_to_download:
                thread = threading.Thread(
                    target=download_file_thread,
                    args=(remote_path, local_path, file_name, component_type,
                          download_queue, concurrency_limiter, self.dsg_api_browser,
                          self._get_session(), self.download_chunk_size)
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
                            print(f"File completed: {file_name} (Total: {completed_files}/{len(files_to_download)})")
                            
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
                            completed_files += 1  # Count errors as completed to allow dialog to close
                            print(f"File error: {file_name} (Total: {completed_files}/{len(files_to_download)})")
                            
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
        """Ask the user if they want to download files again when they already exist"""
        from .dialogs import ask_download_again
        return ask_download_again(component_type, existing_files, parent or self.parent_window)

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
        return create_default_template(launchers_dir, filename)

    def _replace_hostname_regex_powershell(self, template_content, custom_regex, add_disabled_message=False):
        """Replace the hostname detection regex in PowerShell template"""
        return replace_hostname_regex_powershell(template_content, custom_regex, add_disabled_message)
        
    def _replace_hostname_regex_bash(self, template_content, custom_regex, add_disabled_message=False):
        """Replace the hostname detection regex in Bash template using direct string substitution"""
        return replace_hostname_regex_bash(template_content, custom_regex, add_disabled_message)
