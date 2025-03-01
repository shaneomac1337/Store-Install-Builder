import os
import shutil
import customtkinter as ctk
import json
import base64
from webdav3.client import Client
from webdav3.exceptions import WebDavException
from datetime import datetime
from urllib.parse import unquote
import requests
import logging

class WebDAVBrowser:
    def __init__(self, base_url, username=None, password=None):
        if not base_url.startswith('http'):
            base_url = f'https://{base_url}'
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        
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
            return True, "Connected successfully"
        except Exception as e:
            print(f"Connection failed: {str(e)}")
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
                "launcher.wdm.template"
            ],
            "onboarding": [
                "pos.onboarding.json",
                "wdm.onboarding.json"
            ],
            "tokens": [
                "basic_auth_password.txt",
                "form_password.txt"
            ]
        }
        self.webdav_browser = None
        self.window = parent_window  # Store window reference

    def create_webdav_browser(self, base_url, username=None, password=None):
        """Create a new WebDAV browser instance"""
        self.webdav_browser = WebDAVBrowser(base_url, username, password)
        return self.webdav_browser

    def generate(self, config):
        """Generate project from configuration"""
        try:
            # Get absolute output directory path
            output_dir = os.path.abspath(config["output_dir"])
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
                # Create security directory in output
                security_dir = os.path.join(output_dir, "security")
                os.makedirs(security_dir, exist_ok=True)
                
                # Copy certificate to output directory with generic name
                cert_filename = os.path.basename(cert_path)
                dest_path = os.path.join(security_dir, cert_filename)
                shutil.copy2(cert_path, dest_path)
                print(f"Copied certificate from {cert_path} to {dest_path}")
                
                return True
        except Exception as e:
            print(f"Warning: Failed to copy certificate: {str(e)}")
        
        return False

    def _generate_gk_install(self, output_dir, config):
        """Generate GKInstall.ps1 with replaced values"""
        try:
            # Use absolute paths for template and output
            template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "GKInstall.ps1.template")
            output_path = os.path.join(output_dir, 'GKInstall.ps1')
            
            print(f"Generating GKInstall.ps1:")
            print(f"  Template path: {template_path}")
            print(f"  Output path: {output_path}")
            
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
            
            # Define replacements
            replacements = [
                ('$base_url = "test.cse.cloud4retail.co"', f'$base_url = "{config["base_url"]}"'),
                ('$version = "v1.0.0"', f'$version = "{default_version}"'),
                ('$base_install_dir = "C:\\\\gkretail"', f'$base_install_dir = "{config["base_install_dir"]}"'),
                ('$ssl_password = "changeit"', f'$ssl_password = "{config["ssl_password"]}"'),
                ('station.tenantId=001', f'station.tenantId={config["tenant_id"]}'),
            ]
            
            # Add component-specific version replacements with simplified logic
            version_config = f'''
# Component-specific versions
$use_version_override = ${str(use_version_override).lower()}
$pos_version = "{pos_version}"
$wdm_version = "{wdm_version}"

# Function to get the correct version based on system type
function Get-ComponentVersion {{
    param($SystemType)
    
    # If version override is disabled, always use the default version
    if (-not $use_version_override) {{
        return $version
    }}
    
    # If the system type doesn't have a specific version pattern, use the default version
    if (-not $SystemType -or $SystemType -eq "") {{
        return $version
    }}
    
    switch -Regex ($SystemType) {{
        # POS components (both GKR and standard)
        "^.*POS.*|^.*OPOS.*" {{ return $pos_version }}
        
        # WDM components (both GKR and standard)
        "^.*WDM.*|^.*wdm.*" {{ return $wdm_version }}
        
        # For any other system type, use the project version
        default {{ return $version }}
    }}
}}

# Note: This script will use the certificate generated by the GK Install Builder
# The certificate is located in the security directory
'''
            
            # Find the position to insert the component-specific version config
            basic_config_marker = "# Basic configuration"
            template = template.replace(basic_config_marker, f"{basic_config_marker}\n{version_config}")
            
            # Update the download URL to use the component-specific version with fallback logic
            download_url_line = '$download_url = "https://$base_url/dsg/content/cep/SoftwarePackage/$systemType/$version/Launcher.exe"'
            new_download_url_line = '''$component_version = Get-ComponentVersion -SystemType $systemType
# If the component version is empty or null, fall back to the default version
if ([string]::IsNullOrEmpty($component_version)) {
    $component_version = $version
}
$download_url = "https://$base_url/dsg/content/cep/SoftwarePackage/$systemType/$component_version/Launcher.exe"'''
            
            template = template.replace(download_url_line, new_download_url_line)
            
            # Apply all replacements
            for old, new in replacements:
                template = template.replace(old, new)
            
            # Write the modified template to the output file
            with open(output_path, 'w') as f:
                f.write(template)
                
            print(f"Successfully generated GKInstall.ps1 at {output_path}")
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error generating GKInstall.ps1: {error_details}")
            raise Exception(f"Failed to generate GKInstall.ps1: {str(e)}")

    def _generate_onboarding(self, output_dir, config):
        """Generate onboarding.ps1 with replaced values"""
        try:
            # Use absolute paths for template and output
            template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "onboarding.ps1.template")
            output_path = os.path.join(output_dir, 'onboarding.ps1')
            
            print(f"Generating onboarding.ps1:")
            print(f"  Template path: {template_path}")
            print(f"  Output path: {output_path}")
            
            # Check if template exists
            if not os.path.exists(template_path):
                raise Exception(f"Template file not found: {template_path}")
            
            with open(template_path, 'r') as f:
                content = f.read()
            
            # Replace configurations
            content = content.replace(
                'test.cse.cloud4retail.co',
                config['base_url']
            )
            content = content.replace(
                '$username = "launchpad"',
                f'$username = "{config["username"]}"'
            )
            content = content.replace(
                'username = "1001"',
                f'username = "{config["form_username"]}"'
            )
            content = content.replace(
                'tenants/001/',
                f'tenants/{config["tenant_id"]}/'
            )
            
            # Write the modified content
            with open(output_path, 'w') as f:
                f.write(content)
                
            print(f"Successfully generated onboarding.ps1 at {output_path}")
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error generating onboarding.ps1: {error_details}")
            raise Exception(f"Failed to generate onboarding.ps1: {str(e)}")

    def _copy_helper_files(self, output_dir, config):
        """Copy helper files to output directory and handle password files"""
        try:
            # Use absolute paths for source and destination
            script_dir = os.path.dirname(os.path.abspath(__file__))
            helper_src = os.path.join(script_dir, 'helper')
            helper_dst = os.path.join(output_dir, 'helper')
            
            print(f"Copying helper files:")
            print(f"  Source: {helper_src}")
            print(f"  Destination: {helper_dst}")
            
            # Check if source directory exists
            if not os.path.exists(helper_src):
                # Try to find helper directory in parent directory
                parent_helper = os.path.join(os.path.dirname(script_dir), 'helper')
                if os.path.exists(parent_helper):
                    helper_src = parent_helper
                    print(f"  Found helper directory in parent: {helper_src}")
                else:
                    raise FileNotFoundError(f"Helper directory not found at {helper_src} or {parent_helper}")
            
            # Copy entire helper directory structure
            if os.path.exists(helper_dst):
                shutil.rmtree(helper_dst)
            shutil.copytree(helper_src, helper_dst)
            
            # Create password files
            self._create_password_files(helper_dst, config)
            
            # Modify JSON files after copying
            self._modify_json_files(helper_dst, config)
            
            print(f"Successfully copied helper files to {helper_dst}")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error copying helper files: {error_details}")
            raise Exception(f"Failed to copy helper files: {str(e)}")

    def _create_password_files(self, helper_dir, config):
        """Create base64 encoded password files"""
        try:
            tokens_dir = os.path.join(helper_dir, "tokens")
            os.makedirs(tokens_dir, exist_ok=True)

            # Create basic auth password file
            basic_auth_password = config.get("basic_auth_password", "")
            if basic_auth_password:
                encoded_basic = base64.b64encode(basic_auth_password.encode()).decode()
                basic_auth_path = os.path.join(tokens_dir, "basic_auth_password.txt")
                with open(basic_auth_path, 'w') as f:
                    f.write(encoded_basic)

            # Create form password file
            form_password = config.get("form_password", "")
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

    def prepare_offline_package(self, config, selected_components):
        try:
            output_dir = config.get("output_dir", "generated_scripts")
            default_version = config.get("version", "v1.0.0")
            use_version_override = config.get("use_version_override", False)
            
            # Get component-specific versions
            pos_version = config.get("pos_version", default_version)
            wdm_version = config.get("wdm_version", default_version)
            
            print(f"\nPreparing offline package:")
            print(f"Output dir: {output_dir}")
            print(f"Default version: {default_version}")
            print(f"Version override enabled: {use_version_override}")
            print(f"POS version: {pos_version}")
            print(f"WDM version: {wdm_version}")
            print(f"Selected components: {selected_components}")
            
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
            
            downloaded_files = []
            
            # Helper function to determine the correct version to use
            def get_component_version(system_type):
                # If version override is disabled, always use the default version
                if not use_version_override:
                    return default_version
                
                # If system type is empty, use default version
                if not system_type or system_type == "":
                    return default_version
                
                # Check system type patterns - simplified to just POS and WDM
                if "POS" in system_type or "OPOS" in system_type:
                    return pos_version
                elif "WDM" in system_type or "wdm" in system_type:
                    return wdm_version
                else:
                    # For any other system type, use the project version
                    return default_version
            
            # Download components
            if "POS" in selected_components:
                pos_dir = os.path.join(output_dir, "offline_package_POS")
                print(f"\nProcessing POS component...")
                print(f"Output directory: {pos_dir}")
                os.makedirs(pos_dir, exist_ok=True)
                
                # Determine system type and version
                pos_system_type = config.get("pos_system_type", "CSE-OPOS-CLOUD")
                version_to_use = get_component_version(pos_system_type)
                
                print(f"Using system type: {pos_system_type}")
                print(f"Using version: {version_to_use}")
                
                # Navigate to version directory
                pos_version_path = f"/SoftwarePackage/{pos_system_type}/{version_to_use}"
                print(f"Checking version directory: {pos_version_path}")
                
                try:
                    files = self.webdav_browser.list_directories(pos_version_path)
                    print(f"Found files: {files}")
                    
                    # Download files
                    for file in files:
                        if not file['is_directory']:
                            file_name = file['name']
                            if file_name.endswith('.exe') or file_name.endswith('.jar'):
                                print(f"\nDownloading {file_name}...")
                                remote_path = f"{pos_version_path}/{file_name}"
                                local_path = os.path.join(pos_dir, file_name)
                                
                                try:
                                    self.webdav_browser.client.download(remote_path, local_path)
                                    print(f"Successfully downloaded to {local_path}")
                                    downloaded_files.append(f"POS: {file_name}")
                                except Exception as e:
                                    print(f"Error downloading {file_name}: {e}")
                
                except Exception as e:
                    print(f"Error accessing POS version directory: {e}")
                    raise
            
            if "WDM" in selected_components:
                wdm_dir = os.path.join(output_dir, "offline_package_WDM")
                print(f"\nProcessing WDM component...")
                print(f"Output directory: {wdm_dir}")
                os.makedirs(wdm_dir, exist_ok=True)
                
                # Determine system type and version
                wdm_system_type = config.get("wdm_system_type", "CSE-wdm")
                version_to_use = get_component_version(wdm_system_type)
                
                print(f"Using system type: {wdm_system_type}")
                print(f"Using version: {version_to_use}")
                
                # Navigate to version directory
                wdm_version_path = f"/SoftwarePackage/{wdm_system_type}/{version_to_use}"
                print(f"Checking version directory: {wdm_version_path}")
                
                try:
                    files = self.webdav_browser.list_directories(wdm_version_path)
                    print(f"Found files: {files}")
                    
                    # Download files
                    for file in files:
                        if not file['is_directory']:
                            file_name = file['name']
                            if file_name.endswith('.exe') or file_name.endswith('.jar'):
                                print(f"\nDownloading {file_name}...")
                                remote_path = f"{wdm_version_path}/{file_name}"
                                local_path = os.path.join(wdm_dir, file_name)
                                
                                try:
                                    self.webdav_browser.client.download(remote_path, local_path)
                                    print(f"Successfully downloaded to {local_path}")
                                    downloaded_files.append(f"WDM: {file_name}")
                                except Exception as e:
                                    print(f"Error downloading {file_name}: {e}")
                
                except Exception as e:
                    print(f"Error accessing WDM version directory: {e}")
                    raise
            
            # Create summary
            if downloaded_files:
                success_message = "Downloaded files:\n" + "\n".join(downloaded_files)
                success_message += f"\n\nFiles saved in: {output_dir}"
                return True, success_message
            else:
                return False, "No files were downloaded"
            
        except Exception as e:
            print(f"\nError in prepare_offline_package: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Failed to create offline package: {str(e)}" 