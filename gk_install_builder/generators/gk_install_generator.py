"""
GK Install Script Generator

This module contains the main function for generating GKInstall scripts
with platform-specific configurations and detection logic.
"""

import os

# Support both package-relative imports (for tests/package use) and direct imports (for running app)
try:
    from ..utils import setup_firebird_environment_variables, determine_gk_install_paths, write_installation_script
except ImportError:
    from utils.environment_setup import setup_firebird_environment_variables
    from utils.file_operations import determine_gk_install_paths, write_installation_script


def generate_gk_install(output_dir, config, detection_manager,
                        replace_hostname_regex_powershell_func,
                        replace_hostname_regex_bash_func,
                        script_dir):
    """
    Generate GKInstall script with replaced values based on platform

    Args:
        output_dir: Output directory for generated script
        config: Configuration dictionary
        detection_manager: DetectionManager instance
        replace_hostname_regex_powershell_func: Function to replace PowerShell hostname regex
        replace_hostname_regex_bash_func: Function to replace Bash hostname regex
        script_dir: Directory containing script templates

    Returns:
        None (writes files to disk)

    Raises:
        Exception: If template file not found or generation fails
    """
    try:
        # Get platform from config (default to Windows if not specified)
        platform = config.get("platform", "Windows")

        # Get hostname detection setting
        use_hostname_detection = config.get("use_hostname_detection", True)

        # Load detection configuration if available
        if "detection_config" in config:
            detection_manager.set_config(config["detection_config"])
        else:
            # If no detection_config is available but detection is enabled,
            # initialize with default settings based on platform and component type
            if detection_manager.is_detection_enabled():
                # Create a default detection configuration
                default_config = {
                    "file_detection_enabled": True,
                    "use_base_directory": True,
                    "base_directory": "C:\\gkretail\\stations" if platform == "Windows" else "/usr/local/gkretail/stations"
                }
                detection_manager.set_config(default_config)

                # Add this config back to main config to save for future use
                config["detection_config"] = default_config

                print("Initializing detection with default settings:")
                print(f"Base directory: {default_config['base_directory']}")

        # Set environment variables for Firebird
        setup_firebird_environment_variables(config, platform)

        # Determine template and output paths based on platform
        template_path, output_path, template_filename, output_filename = determine_gk_install_paths(
            platform, output_dir, script_dir
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

        # Apply all replacements to the template
        for old, new in replacements:
            template = template.replace(old, new)

        # Replace FILE_DETECTION_ENABLED placeholder
        file_detection_enabled = detection_manager.is_file_detection_enabled()
        template = template.replace("@FILE_DETECTION_ENABLED@", "True" if file_detection_enabled else "False")

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
                    template = replace_hostname_regex_powershell_func(template, custom_regex)
                else:
                    # Replace the hostname detection regex in Bash
                    template = replace_hostname_regex_bash_func(template, custom_regex)

        # Handle hostname environment detection
        hostname_env_detection = detection_manager.get_hostname_env_detection()
        print(f"  Hostname environment detection: {hostname_env_detection}")

        # Only enable environment detection if both hostname detection is enabled AND env detection is enabled
        if use_hostname_detection and hostname_env_detection:
            # Get configured group mappings
            group_mappings = detection_manager.get_all_group_mappings()
            env_group = group_mappings.get("env", 1)
            store_group = group_mappings.get("store", 2)
            ws_group = group_mappings.get("workstation", 3)

            # Insert hostname environment detection code
            if platform == "Windows":
                # Get the configured regex pattern for hostname detection
                hostname_regex = detection_manager.get_hostname_regex("windows")

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
                    Write-Host "    ✓ Matched environment: $($selectedEnv.name)"
                    return $selectedEnv
                }} else {{
                    Write-Host "    ✗ ERROR: Environment '$hostnameEnv' detected from hostname but not configured!" -ForegroundColor Red
                    Write-Host ""
                    Show-Environments
                    Write-Host ""
                    Write-Host "Please add environment '$hostnameEnv' to your configuration." -ForegroundColor Yellow
                    exit 1
                }}
            }} else {{
                Write-Host "    ✗ Regex matched but does not have 3 capture groups (need: Environment, Store, Workstation)"
            }}
        }} else {{
            Write-Host "    Hostname does not match the configured pattern"
        }}
    }} catch {{
        Write-Host "    Error during hostname detection: $_"
    }}

    # Priority 3: File detection from .station files
    Write-Host "[3] File Detection: Checking for environment in .station file..."
    '''
                # Replace the placeholder
                template = template.replace("# HOSTNAME_ENV_DETECTION_PLACEHOLDER", hostname_env_code)
                # Update priority numbers: file detection becomes Priority 3, interactive becomes Priority 4
                template = template.replace("# Priority 2: Environment file detection from .station files", "# Priority 3: Environment file detection from .station files")
                template = template.replace('Write-Host "[2] File Detection: Checking for environment in .station file..."', 'Write-Host "[3] File Detection: Checking for environment in .station file..."')
                template = template.replace("# Priority 3: Interactive prompt", "# Priority 4: Interactive prompt")
                template = template.replace('Write-Host "[3] Interactive Prompt', 'Write-Host "[4] Interactive Prompt')
            else:
                # Linux bash version
                # Get the configured regex pattern for hostname detection
                hostname_regex = detection_manager.get_hostname_regex("linux")

                hostname_env_code = f'''# Priority 2: Hostname environment detection
  echo "[2] Hostname Detection: Extracting environment from hostname..." >&2

  local hostname=$(hostname)
  echo "    Computer name: $hostname" >&2

  # Use the configured hostname regex to extract environment (group {env_group}), store (group {store_group}), and workstation (group {ws_group})
  # Regex pattern: {hostname_regex}
  # Enable case-insensitive matching
  shopt -s nocasematch
  if [[ "$hostname" =~ {hostname_regex} ]]; then
    shopt -u nocasematch  # Restore default
    if [ ${{#BASH_REMATCH[@]}} -ge 4 ]; then
      # 3-group regex: Environment, Store, Workstation
      local hostname_env="${{BASH_REMATCH[{env_group}]}}"
      echo "    Extracted environment from hostname: $hostname_env" >&2
      local selected
      if [ "$JQ_AVAILABLE" = true ]; then
        selected=$(echo "$environments" | jq --arg alias "$hostname_env" '.environments[] | select(.alias == $alias)')
      else
        # Fallback: use bash to find the environment by alias
        selected=$(json_select_by_alias "$environments" "$hostname_env")
      fi
      if [ -n "$selected" ]; then
        echo "    ✓ Matched environment" >&2
        echo "$selected"
        return 0
      else
        echo "    ✗ Environment '$hostname_env' detected from hostname but not configured!" >&2
        echo "" >&2
        show_environments
        echo "" >&2
        echo "    Falling back to manual environment selection..." >&2
        # Don't exit - fall through to file detection and then interactive prompt
      fi
    else
      echo "    ✗ Regex matched but does not have 3 capture groups (need: Environment, Store, Workstation)" >&2
    fi
  else
    shopt -u nocasematch  # Restore default
    echo "    Hostname does not match the configured pattern" >&2
  fi

  # Priority 3: File detection from .station files
  echo "[3] File Detection: Checking for environment in .station file..." >&2
  '''
                # Replace the placeholder
                template = template.replace("# HOSTNAME_ENV_DETECTION_PLACEHOLDER", hostname_env_code)
                # Update priority numbers: file detection becomes Priority 3, interactive becomes Priority 4
                template = template.replace("# Priority 2: Environment file detection from .station files", "# Priority 3: Environment file detection from .station files")
                template = template.replace('echo "[2] File Detection: Checking for environment in .station file..." >&2', 'echo "[3] File Detection: Checking for environment in .station file..." >&2')
                template = template.replace("# Priority 3: Interactive prompt", "# Priority 4: Interactive prompt")
                template = template.replace('echo "[3] Interactive Prompt', 'echo "[4] Interactive Prompt')
        else:
            # Remove the placeholder when disabled
            template = template.replace("# HOSTNAME_ENV_DETECTION_PLACEHOLDER\n    \n    ", "")
            template = template.replace("# HOSTNAME_ENV_DETECTION_PLACEHOLDER\n  \n  ", "")

        # Replace hostname Store/Workstation detection with appropriate code
        if platform == "Windows":
            # Check if hostname detection is enabled
            if use_hostname_detection:
                hostname_regex = detection_manager.get_hostname_regex("windows")

                # Get configured group mappings
                group_mappings = detection_manager.get_all_group_mappings()
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
            else:
                # Hostname detection disabled - use never-match pattern for consistent structure
                store_workstation_code = '''Write-Host "Hostname detection is disabled in configuration - skipping hostname detection" -ForegroundColor Yellow
        if ($hs -match '^NEVER_MATCH_THIS_HOSTNAME_PATTERN$') {
            # Pattern like R005-101 or SOMENAME-1674-101 where last part is digits
            $storeId = $matches[2]
            $workstationId = $matches[3]

            # If storeId contains a dash, it might be SOMENAME-1674-101 format
            if ($storeId -match '.*-(\\d{4})$') {
                $storeNumber = $matches[1]
            } else {
                # Direct format like R005-101
                $storeNumber = $storeId
            }

            # Validate extracted parts
            if ($storeNumber -match '^[A-Za-z0-9_.-]+$') {
                if ($workstationId -match '^[0-9]+$') {
                    $hostnameDetected = $true
                    Write-Host "Successfully detected values from hostname:"
                    Write-Host "Store Number: $storeNumber"
                    Write-Host "Workstation ID: $workstationId"
                }
            }
        }'''

            # Replace the placeholder
            template = template.replace("# HOSTNAME_STORE_WORKSTATION_DETECTION_PLACEHOLDER", store_workstation_code)

            # Handle file detection
            file_detection_enabled = detection_manager.is_file_detection_enabled()

            # Determine the message to show based on whether file detection is enabled
            if file_detection_enabled:
                file_enabled_flag = "$true"
                file_detection_message = ""  # No special message, detection is active
                never_match_comment = ""
            else:
                file_enabled_flag = "$true"  # Keep true but use never-match paths
                file_detection_message = 'Write-Host "File detection is disabled in configuration - skipping file detection" -ForegroundColor Yellow\n'
                never_match_comment = "# File detection disabled - using never-match pattern for consistent structure\n        "

            # Evaluate all Python expressions before building the string
            using_base_dir = str(detection_manager.is_using_base_directory()).lower()
            using_custom_paths = "false" if using_base_dir == "true" else "true"
            base_dir_value = detection_manager.get_base_directory().replace('\\', '\\\\') if file_detection_enabled else "NEVER_MATCH_BASE_DIR"
            pos_file = detection_manager.detection_config["detection_files"]["POS"].replace('\\', '\\\\') if file_detection_enabled else "NEVER_MATCH_FILE_PATH"
            wdm_file = detection_manager.detection_config["detection_files"]["WDM"].replace('\\', '\\\\') if file_detection_enabled else "NEVER_MATCH_FILE_PATH"
            flow_file = detection_manager.detection_config["detection_files"]["FLOW-SERVICE"].replace('\\', '\\\\') if file_detection_enabled else "NEVER_MATCH_FILE_PATH"
            lpa_file = detection_manager.detection_config["detection_files"]["LPA-SERVICE"].replace('\\', '\\\\') if file_detection_enabled else "NEVER_MATCH_FILE_PATH"
            sh_file = detection_manager.detection_config["detection_files"]["STOREHUB-SERVICE"].replace('\\', '\\\\') if file_detection_enabled else "NEVER_MATCH_FILE_PATH"
            pos_filename = detection_manager.get_custom_filename("POS") if file_detection_enabled else "NEVER_MATCH.station"
            wdm_filename = detection_manager.get_custom_filename("WDM") if file_detection_enabled else "NEVER_MATCH.station"
            flow_filename = detection_manager.get_custom_filename("FLOW-SERVICE") if file_detection_enabled else "NEVER_MATCH.station"
            lpa_filename = detection_manager.get_custom_filename("LPA-SERVICE") if file_detection_enabled else "NEVER_MATCH.station"
            sh_filename = detection_manager.get_custom_filename("STOREHUB-SERVICE") if file_detection_enabled else "NEVER_MATCH.station"

            # Build the comprehensive station detection code
            # This includes both base directory and custom paths modes
            station_detection_code = f'''
        {never_match_comment}# File detection for the current component ($ComponentType)
        $fileDetectionEnabled = {file_enabled_flag}
        $componentType = $ComponentType

        # Check if we're using base directory or custom paths
        $useBaseDirectory = "{using_base_dir}".ToLower()

        if ($useBaseDirectory -eq "true") {{
            # Use base directory approach
            $basePath = "{base_dir_value}"
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
                "POS" = "{pos_file}";
                "WDM" = "{wdm_file}";
                "FLOW-SERVICE" = "{flow_file}";
                "LPA-SERVICE" = "{lpa_file}";
                "STOREHUB-SERVICE" = "{sh_file}"
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
'''

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
                    print(f"Added dynamic station detection code to PowerShell script")
                else:
                    print(f"Added station detection code with never-match pattern to PowerShell script (file detection disabled)")
            else:
                print(f"Warning: Could not find insertion point for station detection code in PowerShell script")

        else:
            # Linux (Bash) version
            # Check if hostname detection is enabled
            if use_hostname_detection:
                hostname_regex = detection_manager.get_hostname_regex("linux")

                # Get configured group mappings
                group_mappings = detection_manager.get_all_group_mappings()
                env_group = group_mappings.get("env", 1)
                store_group = group_mappings.get("store", 2)
                ws_group = group_mappings.get("workstation", 3)

                if hostname_env_detection:
                    # 3-group pattern: Use configured group mappings
                    store_workstation_code = rf'''# Extract the last part (workstation ID)
    # Enable case-insensitive matching
    shopt -s nocasematch
    if [[ "$hs" =~ {hostname_regex} ]]; then
      shopt -u nocasematch  # Restore default
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
    else
      shopt -u nocasematch  # Restore default
    fi'''
                else:
                    # 2-group pattern: Use configured group mappings (store and workstation only)
                    store_workstation_code = rf'''# Extract the last part (workstation ID)
    # Enable case-insensitive matching
    shopt -s nocasematch
    if [[ "$hs" =~ {hostname_regex} ]]; then
      shopt -u nocasematch  # Restore default
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
    else
      shopt -u nocasematch  # Restore default
    fi'''
            else:
                # Hostname detection disabled - use never-match pattern for consistent structure
                store_workstation_code = '''# Extract the last part (workstation ID)
    echo "Hostname detection is disabled in configuration - skipping hostname detection"
    if [[ "$hs" =~ ^NEVER_MATCH_THIS_HOSTNAME_PATTERN$ ]]; then
      storeId="${BASH_REMATCH[2]}"
      workstationId="${BASH_REMATCH[3]}"

      # If storeId contains a dash, it might be SOMENAME-1674-101 format
      if [[ "$storeId" =~ .*-([0-9]{4})$ ]]; then
        storeNumber="${BASH_REMATCH[1]}"
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

            # Handle file detection for Linux
            file_detection_enabled = detection_manager.is_file_detection_enabled()

            # Determine the message to show based on whether file detection is enabled
            if file_detection_enabled:
                file_detection_message = ""  # No special message, detection is active
                never_match_comment = ""
            else:
                file_detection_message = 'echo "File detection is disabled in configuration - skipping file detection"\n'
                never_match_comment = "# File detection disabled - using never-match pattern for consistent structure\n"

            # Get the detection configuration values
            using_base_dir_bool = str(detection_manager.is_using_base_directory())
            base_dir_value = detection_manager.get_base_directory() if file_detection_enabled else "NEVER_MATCH_BASE_DIR"
            pos_file = detection_manager.detection_config["detection_files"]["POS"] if file_detection_enabled else "NEVER_MATCH_FILE_PATH"
            wdm_file = detection_manager.detection_config["detection_files"]["WDM"] if file_detection_enabled else "NEVER_MATCH_FILE_PATH"
            flow_file = detection_manager.detection_config["detection_files"]["FLOW-SERVICE"] if file_detection_enabled else "NEVER_MATCH_FILE_PATH"
            lpa_file = detection_manager.detection_config["detection_files"]["LPA-SERVICE"] if file_detection_enabled else "NEVER_MATCH_FILE_PATH"
            sh_file = detection_manager.detection_config["detection_files"]["STOREHUB-SERVICE"] if file_detection_enabled else "NEVER_MATCH_FILE_PATH"
            pos_filename = detection_manager.get_custom_filename("POS") if file_detection_enabled else "NEVER_MATCH.station"
            wdm_filename = detection_manager.get_custom_filename("WDM") if file_detection_enabled else "NEVER_MATCH.station"
            flow_filename = detection_manager.get_custom_filename("FLOW-SERVICE") if file_detection_enabled else "NEVER_MATCH.station"
            lpa_filename = detection_manager.get_custom_filename("LPA-SERVICE") if file_detection_enabled else "NEVER_MATCH.station"
            sh_filename = detection_manager.get_custom_filename("STOREHUB-SERVICE") if file_detection_enabled else "NEVER_MATCH.station"

            # Build the comprehensive station detection code for Linux
            station_detection_code = f'''
{never_match_comment}# File detection for the current component ($COMPONENT_TYPE)
fileDetectionEnabled=true
componentType="$COMPONENT_TYPE"

# Check if we're using base directory or custom paths
useBaseDirectory="{using_base_dir_bool}"

if [ "$useBaseDirectory" = "True" ]; then
    # Use base directory approach
    basePath="{base_dir_value}"
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
    customPaths["POS"]="{pos_file}"
    customPaths["WDM"]="{wdm_file}"
    customPaths["FLOW-SERVICE"]="{flow_file}"
    customPaths["LPA-SERVICE"]="{lpa_file}"
    customPaths["STOREHUB-SERVICE"]="{sh_file}"

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
'''

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
