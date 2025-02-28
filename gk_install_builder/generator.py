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
            output_dir = config["output_dir"]
            os.makedirs(output_dir, exist_ok=True)
            
            # Create project structure
            self._create_directory_structure(output_dir)
            
            # Generate main scripts by modifying the original files
            self._generate_gk_install(output_dir, config)
            self._generate_onboarding(output_dir, config)
            
            # Copy and modify helper files
            self._copy_helper_files(output_dir, config)
            
            self._show_success(f"Project generated in: {output_dir}")
        except Exception as e:
            self._show_error(f"Failed to generate project: {str(e)}")

    def _create_directory_structure(self, output_dir):
        """Create the project directory structure"""
        for dir_name in self.helper_structure.keys():
            os.makedirs(os.path.join(output_dir, "helper", dir_name), exist_ok=True)

    def _generate_gk_install(self, output_dir, config):
        """Generate GKInstall.ps1 with replaced values"""
        try:
            with open('GKInstall.ps1', 'r') as f:
                content = f.read()
            
            # Replace the base URL and other configurations
            content = content.replace(
                'test.cse.cloud4retail.co',
                config['base_url']
            )
            content = content.replace(
                '$version = "v1.0.0"',
                f'$version = "{config["version"]}"'
            )
            content = content.replace(
                '$base_install_dir = "C:\\gkretail"',
                f'$base_install_dir = "{config["base_install_dir"]}"'
            )
            # Replace system types
            content = content.replace(
                '"GKR-OPOS-CLOUD"',
                f'"{config["pos_system_type"]}"'
            )
            content = content.replace(
                '"CSE-wdm"',
                f'"{config["wdm_system_type"]}"'
            )
            
            # Write the modified content
            with open(os.path.join(output_dir, 'GKInstall.ps1'), 'w') as f:
                f.write(content)
                
        except Exception as e:
            raise Exception(f"Failed to generate GKInstall.ps1: {str(e)}")

    def _generate_onboarding(self, output_dir, config):
        """Generate onboarding.ps1 with replaced values"""
        try:
            with open('onboarding.ps1', 'r') as f:
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
            with open(os.path.join(output_dir, 'onboarding.ps1'), 'w') as f:
                f.write(content)
                
        except Exception as e:
            raise Exception(f"Failed to generate onboarding.ps1: {str(e)}")

    def _copy_helper_files(self, output_dir, config):
        """Copy helper files to output directory and handle password files"""
        try:
            # Copy entire helper directory structure
            if os.path.exists('helper'):
                helper_dst = os.path.join(output_dir, 'helper')
                if os.path.exists(helper_dst):
                    shutil.rmtree(helper_dst)
                shutil.copytree('helper', helper_dst)
                
                # Create password files
                self._create_password_files(helper_dst, config)
                
                # Modify JSON files after copying
                self._modify_json_files(helper_dst, config)
            else:
                raise FileNotFoundError("Helper directory not found")

        except Exception as e:
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
            version = config.get("version", "v1.0.0")
            
            print(f"\nPreparing offline package:")
            print(f"Output dir: {output_dir}")
            print(f"Version: {version}")
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
            
            # Download components
            if "POS" in selected_components:
                pos_dir = os.path.join(output_dir, "offline_package_POS")
                print(f"\nProcessing POS component...")
                print(f"Output directory: {pos_dir}")
                os.makedirs(pos_dir, exist_ok=True)
                
                # Navigate to version directory
                pos_version_path = f"/SoftwarePackage/CSE-OPOS-CLOUD/{version}"
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
                
                # Navigate to version directory
                wdm_version_path = f"/SoftwarePackage/CSE-wdm/{version}"
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