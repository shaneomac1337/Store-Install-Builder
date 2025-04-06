import os
import json

class DetectionManager:
    """Manages store and workstation ID automatic detection settings"""
    
    def __init__(self):
        self.detection_config = {
            "file_detection_enabled": False,
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
        if self.detection_config["use_base_directory"] and self.detection_config["base_directory"]:
            filename = self.detection_config["custom_filenames"].get(component_type, f"{component_type}.station")
            return os.path.join(self.detection_config["base_directory"], filename)
        
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
            $fileDetected = $false
            if ($storeNumber -and $workstationId -match '^\d{{3}}$') {{
                $fileDetected = $true
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
        fileDetected=false
        
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
        if [ -n "$storeNumber" ] && [[ "$workstationId" =~ ^[0-9]{{3}}$ ]]; then
            fileDetected=true
            echo "Successfully detected values from file:"
            echo "Store Number: $storeNumber"
            echo "Workstation ID: $workstationId"
        fi
    else
        echo "Station file not found at: $stationFilePath"
    fi
fi
''' 