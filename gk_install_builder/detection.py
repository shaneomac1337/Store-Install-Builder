import os
import json

class DetectionManager:
    """Manages store and workstation ID automatic detection settings"""
    
    def __init__(self):
        self.detection_config = {
            "file_detection_enabled": True,
            "use_base_directory": True,
            "base_directory": "",
            "custom_filenames": {
                "POS": "POS.station",
                "WDM": "WDM.station",
                "FLOW-SERVICE": "FLOW-SERVICE.station",
                "LPA-SERVICE": "LPA.station",
                "STOREHUB-SERVICE": "SH.station"
            },
            "detection_files": {
                "POS": "",
                "WDM": "",
                "FLOW-SERVICE": "",
                "LPA-SERVICE": "",
                "STOREHUB-SERVICE": ""
            },
            "hostname_detection": {
                "windows_regex": r"([^-]+)-([0-9]{3})$",
                "linux_regex": r"([^-]+)-([0-9]+)$",
                "test_hostname": "STORE-1234-101"
            }
        }
    
    def set_file_path(self, component_type, file_path):
        """Set the detection file path for a specific component"""
        if component_type in self.detection_config["detection_files"]:
            self.detection_config["detection_files"][component_type] = file_path
            return True
        return False
    
    def get_file_path(self, component_type):
        """Get the detection file path for a specific component"""
        # If using base directory, combine it with the custom filename
        if self.detection_config["use_base_directory"]:
            base_dir = self.detection_config["base_directory"]
            
            # If base_directory is empty, use a default based on platform
            if not base_dir:
                # Check for platform
                import platform
                is_windows = platform.system() == "Windows"
                
                # Set default base directory based on platform
                if is_windows:
                    base_dir = "C:\\gkretail\\stations"
                else:
                    base_dir = "/usr/local/gkretail/stations"
                
                # Update the config with this default
                self.detection_config["base_directory"] = base_dir
                print(f"Using default station files directory: {base_dir}")
            
            filename = self.detection_config["custom_filenames"].get(component_type, f"{component_type}.station")
            return os.path.join(base_dir, filename)
        
        # Otherwise return the custom path if set
        return self.detection_config["detection_files"].get(component_type, "")
    
    def set_custom_filename(self, component_type, filename):
        """Set a custom filename for a component when using base directory"""
        if component_type in self.detection_config["custom_filenames"]:
            self.detection_config["custom_filenames"][component_type] = filename
            return True
        return False
    
    def get_custom_filename(self, component_type):
        """Get the custom filename for a component"""
        return self.detection_config["custom_filenames"].get(component_type, f"{component_type}.station")
    
    def set_base_directory(self, directory):
        """Set the base directory for station files"""
        self.detection_config["base_directory"] = directory
    
    def get_base_directory(self):
        """Get the base directory for station files"""
        return self.detection_config["base_directory"]
    
    def use_base_directory(self, use=True):
        """Set whether to use base directory approach"""
        self.detection_config["use_base_directory"] = use
    
    def is_using_base_directory(self):
        """Check if using base directory approach"""
        return self.detection_config["use_base_directory"]
    
    def enable_file_detection(self, enabled=True):
        """Enable or disable file detection"""
        self.detection_config["file_detection_enabled"] = enabled
    
    def is_file_detection_enabled(self):
        """Check if file detection is enabled"""
        return self.detection_config["file_detection_enabled"]
    
    # Add alias methods for the renamed functions
    def enable_detection(self, enabled=True):
        """Enable or disable station detection (alias for enable_file_detection)"""
        return self.enable_file_detection(enabled)
    
    def is_detection_enabled(self):
        """Check if station detection is enabled (alias for is_file_detection_enabled)"""
        return self.is_file_detection_enabled()
    
    def get_config(self):
        """Get the full detection configuration"""
        return self.detection_config
    
    def set_config(self, config):
        """Set the detection configuration from a dictionary"""
        if "file_detection_enabled" in config:
            self.detection_config["file_detection_enabled"] = config["file_detection_enabled"]
        
        if "use_base_directory" in config:
            self.detection_config["use_base_directory"] = config["use_base_directory"]
            
        if "base_directory" in config:
            self.detection_config["base_directory"] = config["base_directory"]
        
        if "custom_filenames" in config:
            for component, filename in config["custom_filenames"].items():
                if component in self.detection_config["custom_filenames"]:
                    self.detection_config["custom_filenames"][component] = filename
        
        if "detection_files" in config:
            for component, path in config["detection_files"].items():
                if component in self.detection_config["detection_files"]:
                    self.detection_config["detection_files"][component] = path
                    
        # Copy hostname detection settings if they exist
        if "hostname_detection" in config:
            for key, value in config["hostname_detection"].items():
                self.detection_config["hostname_detection"][key] = value
    
    def get_hostname_regex(self, platform="linux"):
        """Get the hostname detection regex for the specified platform"""
        if platform.lower() == "windows":
            return self.detection_config["hostname_detection"]["windows_regex"]
        else:
            return self.detection_config["hostname_detection"]["linux_regex"]
    
    def set_hostname_regex(self, regex, platform="linux"):
        """Set the hostname detection regex for the specified platform"""
        if platform.lower() == "windows":
            self.detection_config["hostname_detection"]["windows_regex"] = regex
        else:
            self.detection_config["hostname_detection"]["linux_regex"] = regex
    
    def get_test_hostname(self):
        """Get the test hostname for regex validation"""
        return self.detection_config["hostname_detection"]["test_hostname"]
    
    def set_test_hostname(self, hostname):
        """Set the test hostname for regex validation"""
        self.detection_config["hostname_detection"]["test_hostname"] = hostname
    
    def test_hostname_regex(self, hostname, platform="linux"):
        """Test the hostname regex against a sample hostname"""
        import re
        
        regex_pattern = self.get_hostname_regex(platform)
        
        try:
            # Create regex pattern based on platform
            pattern = re.compile(regex_pattern)
            
            # Test against the hostname
            match = pattern.search(hostname)
            
            if match and len(match.groups()) >= 2:
                store_id = match.group(1)
                workstation_id = match.group(2)
                
                # Additional validation based on platform
                if platform.lower() == "windows":
                    # Windows format: Match standard format
                    return {
                        "success": True,
                        "store_id": store_id,
                        "workstation_id": workstation_id
                    }
                else:
                    # Linux - Check if store_id contains a dash for compound format
                    store_number = store_id
                    if "-" in store_id:
                        # Try to extract a 4-digit number after the last dash
                        store_match = re.search(r".*-([0-9]{4})$", store_id)
                        if store_match:
                            store_number = store_match.group(1)
                    
                    # Validate formats similar to the template validation
                    is_valid_store = (
                        re.match(r"^[0-9]{4}$", store_number) or 
                        re.match(r"^[A-Za-z][0-9]{3}$", store_number) or 
                        re.match(r"^[A-Za-z]{2}[0-9]{2}$", store_number)
                    )
                    
                    # Accept workstation IDs of any length as long as they contain only digits
                    is_valid_ws = re.match(r"^[0-9]+$", workstation_id)
                    
                    return {
                        "success": bool(is_valid_store and is_valid_ws),
                        "store_id": store_id,
                        "store_number": store_number,
                        "workstation_id": workstation_id,
                        "is_valid_store": bool(is_valid_store),
                        "is_valid_ws": bool(is_valid_ws)
                    }
            
            return {"success": False, "error": "Regex did not match or insufficient capture groups"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_detection_code(self, component_type, script_type="powershell"):
        """Generate script code for file detection based on component and script type"""
        file_path = self.get_file_path(component_type)
        
        if not file_path or not self.is_detection_enabled():
            return ""
        
        if script_type.lower() == "powershell":
            return self._generate_powershell_detection(component_type, file_path)
        else:  # bash
            return self._generate_bash_detection(component_type, file_path)
    
    def _generate_powershell_detection(self, component_type, file_path):
        """Generate PowerShell code for file detection"""
        return f'''
# File detection for {component_type}
$fileDetectionEnabled = $true
$stationFilePath = "{file_path.replace('\\', '\\\\')}"

# Check if hostname detection failed and file detection is enabled
if (-not $hostnameDetected -and $fileDetectionEnabled) {{
    Write-Host "Trying file detection using $stationFilePath"
    
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
'''
    
    def _generate_bash_detection(self, component_type, file_path):
        """Generate Bash code for file detection"""
        return f'''
# File detection for {component_type}
fileDetectionEnabled=true
stationFilePath="{file_path}"

# Check if hostname detection failed and file detection is enabled
if [ "$hostnameDetected" = false ] && [ "$fileDetectionEnabled" = true ]; then
    echo "Trying file detection using $stationFilePath"
    
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