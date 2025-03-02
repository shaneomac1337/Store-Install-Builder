import os
import re
import json
import shutil
import customtkinter as ctk
import base64
from webdav3.client import Client
from webdav3.exceptions import WebDavException
from datetime import datetime
from urllib.parse import unquote
import requests
import logging
from string import Template
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# Disable insecure request warnings
urllib3.disable_warnings(InsecureRequestWarning)

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
        self.parent_window = parent_window  # Rename to parent_window for consistency

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
            
            # Get system types from config
            pos_system_type = config.get("pos_system_type", "GKR-OPOS-CLOUD")
            wdm_system_type = config.get("wdm_system_type", "CSE-wdm")
            
            print(f"Using system types from config:")
            print(f"  POS System Type: {pos_system_type}")
            print(f"  WDM System Type: {wdm_system_type}")
            
            # Define replacements
            replacements = [
                ('$base_url = "test.cse.cloud4retail.co"', f'$base_url = "{config["base_url"]}"'),
                ('$version = "v1.0.0"', f'$version = "{default_version}"'),
                ('$base_install_dir = "C:\\\\gkretail"', f'$base_install_dir = "{config["base_install_dir"]}"'),
                ('$ssl_password = "changeit"', f'$ssl_password = "{config["ssl_password"]}"'),
                ('station.tenantId=001', f'station.tenantId={config["tenant_id"]}'),
                # Replace hardcoded system types in the if statement
                ('$systemType = if ($ComponentType -eq \'POS\') { "GKR-OPOS-CLOUD" } else { "CSE-wdm" }', 
                 f'$systemType = if ($ComponentType -eq \'POS\') {{ "{pos_system_type}" }} else {{ "{wdm_system_type}" }}'),
                # Replace hardcoded system types in the dictionary
                ('$systemTypes = @{\n    POS = "GKR-OPOS-CLOUD"\n    WDM = "CSE-wdm"', 
                 f'$systemTypes = @{{\n    POS = "{pos_system_type}"\n    WDM = "{wdm_system_type}"'),
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

    def _ask_download_dependencies_only(self, component_type, parent=None, error_message=None):
        """Ask user if they want to download dependencies even if component files are not found"""
        import customtkinter as ctk
        import tkinter as tk
        
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
        dialog.attributes("-topmost", True)
        
        # Make dialog modal
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
        
        # Wait for the dialog to close
        if parent_window:
            parent_window.wait_window(dialog)
        else:
            # If we don't have a parent window, use a different approach
            dialog.wait_window()
        
        return result

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
            
            # Get component dependencies
            component_dependencies = config.get("component_dependencies", {})
            
            print(f"\nPreparing offline package:")
            print(f"Output dir: {output_dir}")
            print(f"Default version: {default_version}")
            print(f"Version override enabled: {use_version_override}")
            print(f"POS version: {pos_version}")
            print(f"WDM version: {wdm_version}")
            print(f"Selected components: {selected_components}")
            print(f"Component dependencies: {component_dependencies}")
            
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
            
            # Helper function to download a file in a separate thread
            def download_file_thread(remote_path, local_path, file_name, component_type):
                try:
                    print(f"\nDownloading {file_name}...")
                    
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
                    
                    print(f"Successfully downloaded to {local_path}")
                    download_queue.put(("success", f"{component_type}: {file_name}"))
                except Exception as e:
                    print(f"Error downloading {file_name}: {e}")
                    download_queue.put(("error", f"Failed to download {file_name}: {str(e)}"))
            
            # Helper function to create a progress dialog
            def create_progress_dialog(parent, total_files):
                import customtkinter as ctk
                
                progress_dialog = ctk.CTkToplevel(parent)
                progress_dialog.title("Downloading Files")
                progress_dialog.geometry("500x400")
                progress_dialog.transient(parent)
                progress_dialog.grab_set()
                progress_dialog.attributes("-topmost", True)
                progress_dialog.focus_force()
                
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
                ).pack(pady=(10, 5), padx=10, anchor="w")
                
                progress_bar = ctk.CTkProgressBar(progress_frame, width=450)
                progress_bar.pack(pady=(0, 10), padx=10)
                progress_bar.set(0)
                
                # Files progress label
                files_label = ctk.CTkLabel(
                    progress_frame,
                    text=f"0/{total_files} files completed",
                    font=("Helvetica", 12)
                )
                files_label.pack(pady=(0, 10), padx=10)
                
                # Current file progress
                ctk.CTkLabel(
                    progress_frame,
                    text="Current File Progress:",
                    font=("Helvetica", 12)
                ).pack(pady=(5, 5), padx=10, anchor="w")
                
                current_file_label = ctk.CTkLabel(
                    progress_frame,
                    text="Waiting to start...",
                    font=("Helvetica", 12)
                )
                current_file_label.pack(pady=(0, 5), padx=10)
                
                current_file_progress = ctk.CTkProgressBar(progress_frame, width=450)
                current_file_progress.pack(pady=(0, 10), padx=10)
                current_file_progress.set(0)
                
                # Create a scrollable frame for the log
                log_frame = ctk.CTkScrollableFrame(progress_frame, width=450, height=120)
                log_frame.pack(fill="both", expand=True, padx=10, pady=10)
                
                # Log label
                log_label = ctk.CTkLabel(
                    log_frame,
                    text="",
                    font=("Helvetica", 10),
                    justify="left",
                    wraplength=430
                )
                log_label.pack(anchor="w", pady=5, padx=5)
                
                return progress_dialog, progress_bar, files_label, current_file_label, current_file_progress, log_label
            
            # Helper function to prompt user for file selection when multiple JAR files are found
            def prompt_for_file_selection(files, component_type, title=None, description=None, file_type=None):
                import customtkinter as ctk
                import tkinter as tk
                
                # Use custom title and description if provided
                title = title or f"Select {component_type} Installer"
                description = description or f"Please select which installer(s) you want to download:"
                
                # Filter for appropriate file types
                if file_type == "zip":
                    installable_files = [file for file in files if not file['is_directory'] and 
                                        file['name'].endswith('.zip')]
                else:
                    installable_files = [file for file in files if not file['is_directory'] and 
                                        (file['name'].endswith('.jar') or file['name'].endswith('.exe'))]
                
                # Separate Launcher.exe from other files (only for regular components)
                if file_type != "zip":
                    launcher_files = [file for file in installable_files if file['name'] == 'Launcher.exe']
                    other_files = [file for file in installable_files if file['name'] != 'Launcher.exe']
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
                dialog.geometry("500x400")
                dialog.attributes("-topmost", True)
                
                # Make dialog modal
                dialog.focus_force()
                dialog.grab_set()
                
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
                    launcher_label = ctk.CTkLabel(
                        dialog,
                        text="Note: Launcher.exe will be downloaded automatically",
                        font=("Helvetica", 12, "italic"),
                        text_color="gray"
                    )
                    launcher_label.pack(pady=(0, 10), padx=20)
                
                # Create a scrollable frame for the checkboxes
                scroll_frame = ctk.CTkScrollableFrame(dialog, width=450, height=200)
                scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
                
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
                for file in other_files:
                    # Only select the latest file by default
                    default_selected = (file == latest_file)
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
                
                # Process Java
                java_path = "/SoftwarePackage/Java"
                print(f"\nChecking Java directory for {component_type}: {java_path}")
                
                try:
                    java_files = self.webdav_browser.list_directories(java_path)
                    print(f"Found Java files: {java_files}")
                    
                    # Prompt user to select Java version
                    selected_java_files = prompt_for_file_selection(
                        java_files, 
                        f"{component_type} Java", 
                        f"Select Java Version for {component_type}", 
                        f"Please select which Java version to download for {component_type}:",
                        "zip"
                    )
                    
                    # Add selected files to dependency files list
                    for file in selected_java_files:
                        file_name = file['name']
                        remote_path = f"{java_path}/{file_name}"
                        local_path = os.path.join(component_dir, "Java_" + file_name)
                        dependency_files.append((remote_path, local_path, file_name, f"{component_type} Java"))
                
                except Exception as e:
                    print(f"Error accessing Java directory: {e}")
                    download_errors.append(f"Failed to access Java directory for {component_type}: {str(e)}")
                
                # Process Tomcat
                tomcat_path = "/SoftwarePackage/Tomcat"
                print(f"\nChecking Tomcat directory for {component_type}: {tomcat_path}")
                
                try:
                    tomcat_files = self.webdav_browser.list_directories(tomcat_path)
                    print(f"Found Tomcat files: {tomcat_files}")
                    
                    # Prompt user to select Tomcat version
                    selected_tomcat_files = prompt_for_file_selection(
                        tomcat_files, 
                        f"{component_type} Tomcat", 
                        f"Select Tomcat Version for {component_type}", 
                        f"Please select which Tomcat version to download for {component_type}:",
                        "zip"
                    )
                    
                    # Add selected files to dependency files list
                    for file in selected_tomcat_files:
                        file_name = file['name']
                        remote_path = f"{tomcat_path}/{file_name}"
                        local_path = os.path.join(component_dir, "Tomcat_" + file_name)
                        dependency_files.append((remote_path, local_path, file_name, f"{component_type} Tomcat"))
                
                except Exception as e:
                    print(f"Error accessing Tomcat directory: {e}")
                    download_errors.append(f"Failed to access Tomcat directory for {component_type}: {str(e)}")
                
                return dependency_files
            
            # Collect all files to download first
            files_to_download = []
            
            # Process POS component
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
                    
                    # Prompt user to select files if multiple JAR/EXE files are found
                    selected_files = prompt_for_file_selection(files, "POS")
                    
                    # Add selected files to download list
                    for file in selected_files:
                        file_name = file['name']
                        remote_path = f"{pos_version_path}/{file_name}"
                        local_path = os.path.join(pos_dir, file_name)
                        files_to_download.append((remote_path, local_path, file_name, "POS"))
                    
                    # Check if no files were found but dependencies are needed
                    if not selected_files and component_dependencies.get("POS", False):
                        # Ask user if they want to download dependencies even though no component files were found
                        if self._ask_download_dependencies_only("POS", dialog_parent):
                            # Download Java and Tomcat for POS
                            dependency_files = download_dependencies_for_component("POS", pos_dir)
                            files_to_download.extend(dependency_files)
                    # Check if dependencies are needed for POS
                    elif component_dependencies.get("POS", False):
                        # Download Java and Tomcat for POS
                        dependency_files = download_dependencies_for_component("POS", pos_dir)
                        files_to_download.extend(dependency_files)
                
                except Exception as e:
                    print(f"Error accessing POS version directory: {e}")
                    # Ask if user wants to download dependencies even though component files couldn't be accessed
                    if component_dependencies.get("POS", False):
                        if self._ask_download_dependencies_only("POS", dialog_parent, error_message=str(e)):
                            # Download Java and Tomcat for POS
                            dependency_files = download_dependencies_for_component("POS", pos_dir)
                            files_to_download.extend(dependency_files)
                    else:
                        raise
            
            # Process WDM component
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
                    
                    # Prompt user to select files if multiple JAR/EXE files are found
                    selected_files = prompt_for_file_selection(files, "WDM")
                    
                    # Add selected files to download list
                    for file in selected_files:
                        file_name = file['name']
                        remote_path = f"{wdm_version_path}/{file_name}"
                        local_path = os.path.join(wdm_dir, file_name)
                        files_to_download.append((remote_path, local_path, file_name, "WDM"))
                    
                    # Check if no files were found but dependencies are needed
                    if not selected_files and component_dependencies.get("WDM", False):
                        # Ask user if they want to download dependencies even though no component files were found
                        if self._ask_download_dependencies_only("WDM", dialog_parent):
                            # Download Java and Tomcat for WDM
                            dependency_files = download_dependencies_for_component("WDM", wdm_dir)
                            files_to_download.extend(dependency_files)
                    # Check if dependencies are needed for WDM
                    elif component_dependencies.get("WDM", False):
                        # Download Java and Tomcat for WDM
                        dependency_files = download_dependencies_for_component("WDM", wdm_dir)
                        files_to_download.extend(dependency_files)
                
                except Exception as e:
                    print(f"Error accessing WDM version directory: {e}")
                    # Ask if user wants to download dependencies even though component files couldn't be accessed
                    if component_dependencies.get("WDM", False):
                        if self._ask_download_dependencies_only("WDM", dialog_parent, error_message=str(e)):
                            # Download Java and Tomcat for WDM
                            dependency_files = download_dependencies_for_component("WDM", wdm_dir)
                            files_to_download.extend(dependency_files)
                    else:
                        raise
            
            # If no files to download, return
            if not files_to_download:
                return False, "No files were selected for download"
            
            # Create progress dialog
            parent = dialog_parent or self.parent_window
            if parent:
                progress_dialog, progress_bar, files_label, current_file_label, current_file_progress, log_label = create_progress_dialog(parent, len(files_to_download))
            
            # Start download threads
            download_threads = []
            for remote_path, local_path, file_name, component_type in files_to_download:
                thread = threading.Thread(
                    target=download_file_thread,
                    args=(remote_path, local_path, file_name, component_type)
                )
                thread.daemon = True
                download_threads.append(thread)
                thread.start()
            
            # Update progress while downloads are running
            if parent:
                log_text = ""
                completed_files = 0
                file_progress = {}  # Track progress for each file
                total_bytes = 0
                downloaded_bytes = 0
                
                # Calculate total bytes if available
                for _, _, file_name, _ in files_to_download:
                    file_progress[file_name] = (0, 0)  # (downloaded, total)
                
                while completed_files < len(files_to_download):
                    try:
                        # Check for new download results
                        while not download_queue.empty():
                            status, data = download_queue.get_nowait()
                            
                            if status == "progress":
                                # Update file progress
                                file_name, component_type, downloaded, total = data
                                file_progress[file_name] = (downloaded, total)
                                
                                # Update current file progress bar and label
                                if total > 0:
                                    current_file_progress.set(downloaded / total)
                                    size_mb = total / (1024 * 1024)
                                    downloaded_mb = downloaded / (1024 * 1024)
                                    current_file_label.configure(
                                        text=f"Downloading {component_type}: {file_name} - {downloaded_mb:.2f} MB / {size_mb:.2f} MB"
                                    )
                                else:
                                    current_file_progress.set(0)
                                    current_file_label.configure(
                                        text=f"Downloading {component_type}: {file_name} - Size unknown"
                                    )
                                
                                # Calculate overall progress based on all files
                                total_bytes = sum(total for _, total in file_progress.values())
                                downloaded_bytes = sum(downloaded for downloaded, _ in file_progress.values())
                                
                                if total_bytes > 0:
                                    overall_progress = downloaded_bytes / total_bytes
                                    progress_bar.set(overall_progress)
                            
                            elif status == "success":
                                downloaded_files.append(data)
                                log_text += f"✓ {data}\n"
                                completed_files += 1
                                
                                # Update files counter
                                files_label.configure(text=f"{completed_files}/{len(files_to_download)} files completed")
                                
                                # Reset current file progress for the next file
                                current_file_progress.set(0)
                                if completed_files == len(files_to_download):
                                    current_file_label.configure(text="All downloads complete!")
                                else:
                                    current_file_label.configure(text="Waiting for next file...")
                            
                            else:  # error
                                download_errors.append(data)
                                log_text += f"✗ {data}\n"
                                completed_files += 1
                                
                                # Update files counter
                                files_label.configure(text=f"{completed_files}/{len(files_to_download)} files completed")
                            
                            # Update log
                            log_label.configure(text=log_text)
                        
                        # Update UI
                        parent.update()
                        time.sleep(0.05)
                        
                    except Exception as e:
                        print(f"Error updating progress: {e}")
                
                # Wait a moment before closing the progress dialog
                time.sleep(1)
                progress_dialog.destroy()
            else:
                # If no parent window, just wait for all threads to complete
                for thread in download_threads:
                    thread.join()
                
                # Process all download results
                while not download_queue.empty():
                    status, data = download_queue.get()
                    if status == "success":
                        downloaded_files.append(data)
                    elif status == "error":
                        download_errors.append(data)
                    # Ignore progress updates when no UI
            
            # Create summary
            if downloaded_files:
                success_message = "Downloaded files:\n" + "\n".join(downloaded_files)
                if download_errors:
                    success_message += "\n\nErrors:\n" + "\n".join(download_errors)
                success_message += f"\n\nFiles saved in: {output_dir}"
                return True, success_message
            else:
                error_message = "No files were downloaded successfully"
                if download_errors:
                    error_message += "\n\nErrors:\n" + "\n".join(download_errors)
                return False, error_message
            
        except Exception as e:
            print(f"\nError in prepare_offline_package: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Failed to create offline package: {str(e)}" 