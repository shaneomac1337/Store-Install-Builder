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
import time
import threading
import queue

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
                    ("CSE-sh-cloud", storehub_service_system_type)
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
                    ("CSE-sh-cloud", storehub_service_system_type)
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
        
        # Check if we have template files in the source directory
        source_launchers_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "helper", "launchers")
        
        # Make sure the source directory exists
        if not os.path.exists(source_launchers_dir):
            print(f"Source launchers directory not found: {source_launchers_dir}")
            # Create the source directory
            os.makedirs(source_launchers_dir, exist_ok=True)
            
            # Create default templates in the source directory
            self._create_default_templates(source_launchers_dir)
        
        # Process each template file
        for filename, settings in template_files.items():
            # Check if the template exists in the source directory
            source_path = os.path.join(source_launchers_dir, filename)
            if not os.path.exists(source_path):
                print(f"Template file not found in source directory: {source_path}")
                # Create default template in the source directory
                self._create_default_template(source_launchers_dir, filename)
            
            # Read the template from the source directory
            try:
                with open(source_path, 'r') as f:
                    template_content = f.read()
                print(f"Loaded template from source: {filename}")
            except Exception as e:
                print(f"Error loading template from source {filename}: {str(e)}")
                continue
            
            # Create a copy of the template content to modify if needed
            modified_template = template_content
            
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
                        
                        # If this key has a setting and the value doesn't contain a placeholder
                        if key in settings and '@' not in value:
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
                
                modified_template = '\n'.join(new_lines)
            else:
                print(f"No settings to apply for {filename}, using default template")
            
            # Write the template to the output file
            output_path = os.path.join(launchers_dir, filename)
            try:
                with open(output_path, 'w') as f:
                    f.write(modified_template)
                print(f"Generated launcher template: {filename}")
            except Exception as e:
                print(f"Error generating launcher template {filename}: {str(e)}")
    
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
applicationServerHttpPort=8280
applicationServerHttpsPort=8643
applicationServerShutdownPort=8006
applicationServerJmxPort=52223
updaterJmxPort=4334
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
applicationServerHttpPort=8380
applicationServerHttpsPort=8743
applicationServerShutdownPort=8007
applicationServerJmxPort=52224
applicationJmsPort=7001
updaterJmxPort=4335
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
firebirdServerPath=@FIREBIRD_SERVER_PATH@
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
                    'tenants/001/',
                    f'tenants/{tenant_id}/'
                )
            else:  # Linux
                # Linux-specific replacements
                content = content.replace(
                    'base_url="test.cse.cloud4retail.co"',
                    f'base_url="{base_url}"'
                )
                content = content.replace(
                    'username="launchpad"',
                    f'username="{username}"'
                )
                content = content.replace(
                    '"1001"',
                    f'"{form_username}"'
                )
                content = content.replace(
                    'tenants/001/',
                    f'tenants/{tenant_id}/'
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
                    
                    # Create JSON files
                    self._create_default_json_files(helper_dst, config)
                    
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

    def _create_default_json_files(self, helper_dir, config):
        """Create default JSON files for onboarding"""
        onboarding_dir = os.path.join(helper_dir, "onboarding")
        os.makedirs(onboarding_dir, exist_ok=True)
        
        # Default JSON templates for different component types
        json_templates = {
            "pos.onboarding.json": '''{"deviceId":"1001","tenant_id":"001","timestamp":"{{TIMESTAMP}}"}''',
            "wdm.onboarding.json": '''{"deviceId":"1001","tenant_id":"001","timestamp":"{{TIMESTAMP}}"}''',
            "flow-service.onboarding.json": '''{"deviceId":"1001","tenant_id":"001","timestamp":"{{TIMESTAMP}}"}''',
            "lpa-service.onboarding.json": '''{"deviceId":"1001","tenant_id":"001","timestamp":"{{TIMESTAMP}}"}''',
            "storehub-service.onboarding.json": '''{"deviceId":"1001","tenant_id":"001","timestamp":"{{TIMESTAMP}}"}'''
        }
        
        # Write JSON files
        for filename, content in json_templates.items():
            # Replace placeholders
            timestamp = int(time.time() * 1000)  # Current time in milliseconds
            content = content.replace("{{TIMESTAMP}}", str(timestamp))
            content = content.replace("001", config.get("tenant_id", "001"))
            content = content.replace("1001", config.get("eh_launchpad_username", "1001"))
            
            # Write file
            file_path = os.path.join(onboarding_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"  Created JSON file: {file_path}")

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
        
        # Make sure the dialog is visible before setting grab
        dialog.update_idletasks()
        dialog.deiconify()
        dialog.wait_visibility()
        dialog.lift()
        dialog.focus_force()
        
        # Center the dialog on the parent window if available
        if parent_window:
            x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - (500 // 2)
            y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - (200 // 2)
            dialog.geometry(f"+{x}+{y}")
        
        # Now that the window is visible, set grab
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
            
            # Get component dependencies
            component_dependencies = config.get("component_dependencies", {})
            
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
                
                progress_dialog = ctk.CTkToplevel(parent)
                progress_dialog.title("Downloading Files")
                progress_dialog.geometry("700x600")  # Increased size to accommodate multiple progress bars
                progress_dialog.transient(parent)
                
                # Make sure the dialog is visible before setting grab
                progress_dialog.update_idletasks()
                progress_dialog.deiconify()
                progress_dialog.wait_visibility()
                progress_dialog.lift()
                progress_dialog.focus_force()
                
                # Center the dialog on the parent window
                x = parent.winfo_x() + (parent.winfo_width() // 2) - (700 // 2)
                y = parent.winfo_y() + (parent.winfo_height() // 2) - (600 // 2)
                progress_dialog.geometry(f"+{x}+{y}")
                
                # Now that the window is visible, set grab
                progress_dialog.grab_set()
                progress_dialog.attributes("-topmost", True)
                
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
                
                files_frame = ctk.CTkScrollableFrame(progress_frame, width=650, height=250)
                files_frame.pack(fill="both", expand=True, padx=10, pady=10)
                
                # Dictionary to store progress bars and labels for each file
                file_progress_widgets = {}
                
                # Create a scrollable frame for the log
                ctk.CTkLabel(
                    progress_frame,
                    text="Download Log:",
                    font=("Helvetica", 12, "bold")
                ).pack(pady=(10, 5), padx=10, anchor="w")
                
                log_frame = ctk.CTkScrollableFrame(progress_frame, width=650, height=120)
                log_frame.pack(fill="both", expand=True, padx=10, pady=10)
                
                # Log label
                log_label = ctk.CTkLabel(
                    log_frame,
                    text="",
                    font=("Helvetica", 10),
                    justify="left",
                    wraplength=630
                )
                log_label.pack(anchor="w", pady=5, padx=5)
                
                return progress_dialog, progress_bar, files_label, files_frame, file_progress_widgets, log_label
            
            # Helper function to prompt user for file selection when multiple JAR files are found
            def prompt_for_file_selection(files, component_type, title=None, description=None, file_type=None, config=None):
                import customtkinter as ctk
                import tkinter as tk
                
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
                
                # Make sure the dialog is visible before setting grab
                dialog.update_idletasks()
                dialog.deiconify()
                dialog.wait_visibility()
                dialog.lift()
                dialog.focus_force()
                
                # Center the dialog on the parent window if available
                if parent:
                    x = parent.winfo_x() + (parent.winfo_width() // 2) - (600 // 2)
                    y = parent.winfo_y() + (parent.winfo_height() // 2) - (500 // 2)
                    dialog.geometry(f"+{x}+{y}")
                
                # Now that the window is visible, set grab
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
                
                return dependency_files
            
            # Collect all files to download first
            files_to_download = []
            
            # Process POS component
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
                        files_to_download.append((remote_path, local_path, file_name, "Flow Service"))
                    
                    # Check if no files were found but dependencies are needed
                    if not selected_files and component_dependencies.get("FLOW-SERVICE", False):
                        # Ask user if they want to download dependencies even though no component files were found
                        if self._ask_download_dependencies_only("Flow Service", dialog_parent):
                            # Download Java and Tomcat for Flow Service
                            dependency_files = download_dependencies_for_component("Flow Service", flow_service_dir)
                            files_to_download.extend(dependency_files)
                    # Check if dependencies are needed for Flow Service
                    elif component_dependencies.get("FLOW-SERVICE", False):
                        # Download Java and Tomcat for Flow Service
                        dependency_files = download_dependencies_for_component("Flow Service", flow_service_dir)
                        files_to_download.extend(dependency_files)
                
                except Exception as e:
                    print(f"Error accessing Flow Service version directory: {e}")
                    # Ask if user wants to download dependencies even though component files couldn't be accessed
                    if component_dependencies.get("FLOW-SERVICE", False):
                        if self._ask_download_dependencies_only("Flow Service", dialog_parent, error_message=str(e)):
                            # Download Java and Tomcat for Flow Service
                            dependency_files = download_dependencies_for_component("Flow Service", flow_service_dir)
                            files_to_download.extend(dependency_files)
                    else:
                        raise
                
                # Copy launcher template
                try:
                    launcher_template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "helper", "launchers", "launcher.flow-service.template")
                    launcher_output_path = os.path.join(flow_service_dir, "launcher.properties.template")
                    shutil.copy(launcher_template_path, launcher_output_path)
                    print(f"Copied Flow Service launcher template to {launcher_output_path}")
                except Exception as e:
                    print(f"Error copying Flow Service launcher template: {e}")
                    download_errors.append(f"Failed to copy Flow Service launcher template: {str(e)}")
            
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
                        files_to_download.append((remote_path, local_path, file_name, "LPA Service"))
                    
                    # Check if no files were found but dependencies are needed
                    if not selected_files and component_dependencies.get("LPA-SERVICE", False):
                        # Ask user if they want to download dependencies even though no component files were found
                        if self._ask_download_dependencies_only("LPA Service", dialog_parent):
                            # Download Java and Tomcat for LPA Service
                            dependency_files = download_dependencies_for_component("LPA Service", lpa_service_dir)
                            files_to_download.extend(dependency_files)
                    # Check if dependencies are needed for LPA Service
                    elif component_dependencies.get("LPA-SERVICE", False):
                        # Download Java and Tomcat for LPA Service
                        dependency_files = download_dependencies_for_component("LPA Service", lpa_service_dir)
                        files_to_download.extend(dependency_files)
                
                except Exception as e:
                    print(f"Error accessing LPA Service version directory: {e}")
                    # Ask if user wants to download dependencies even though component files couldn't be accessed
                    if component_dependencies.get("LPA-SERVICE", False):
                        if self._ask_download_dependencies_only("LPA Service", dialog_parent, error_message=str(e)):
                            # Download Java and Tomcat for LPA Service
                            dependency_files = download_dependencies_for_component("LPA Service", lpa_service_dir)
                            files_to_download.extend(dependency_files)
                    else:
                        raise
                
                # Copy launcher template
                try:
                    launcher_template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "helper", "launchers", "launcher.lpa-service.template")
                    launcher_output_path = os.path.join(lpa_service_dir, "launcher.properties.template")
                    shutil.copy(launcher_template_path, launcher_output_path)
                    print(f"Copied LPA Service launcher template to {launcher_output_path}")
                except Exception as e:
                    print(f"Error copying LPA Service launcher template: {e}")
                    download_errors.append(f"Failed to copy LPA Service launcher template: {str(e)}")
            
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
                        files_to_download.append((remote_path, local_path, file_name, "StoreHub Service"))
                    
                    # Check if no files were found but dependencies are needed
                    if not selected_files and component_dependencies.get("STOREHUB-SERVICE", False):
                        # Ask user if they want to download dependencies even though no component files were found
                        if self._ask_download_dependencies_only("StoreHub Service", dialog_parent):
                            # Download Java and Tomcat for StoreHub Service
                            dependency_files = download_dependencies_for_component("StoreHub Service", storehub_service_dir)
                            files_to_download.extend(dependency_files)
                    # Check if dependencies are needed for StoreHub Service
                    elif component_dependencies.get("STOREHUB-SERVICE", False):
                        # Download Java and Tomcat for StoreHub Service
                        dependency_files = download_dependencies_for_component("StoreHub Service", storehub_service_dir)
                        files_to_download.extend(dependency_files)
                
                except Exception as e:
                    print(f"Error accessing StoreHub Service version directory: {e}")
                    # Ask if user wants to download dependencies even though component files couldn't be accessed
                    if component_dependencies.get("STOREHUB-SERVICE", False):
                        if self._ask_download_dependencies_only("StoreHub Service", dialog_parent, error_message=str(e)):
                            # Download Java and Tomcat for StoreHub Service
                            dependency_files = download_dependencies_for_component("StoreHub Service", storehub_service_dir)
                            files_to_download.extend(dependency_files)
                    else:
                        raise
                
                # Copy launcher template
                try:
                    launcher_template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "helper", "launchers", "launcher.storehub-service.template")
                    launcher_output_path = os.path.join(storehub_service_dir, "launcher.properties.template")
                    shutil.copy(launcher_template_path, launcher_output_path)
                    print(f"Copied StoreHub Service launcher template to {launcher_output_path}")
                except Exception as e:
                    print(f"Error copying StoreHub Service launcher template: {e}")
                    download_errors.append(f"Failed to copy StoreHub Service launcher template: {str(e)}")
            
            # If no files to download, return
            if not files_to_download:
                return False, "No files were selected for download"
            
            # Create progress dialog
            parent = dialog_parent or self.parent_window
            if parent:
                progress_dialog, progress_bar, files_label, files_frame, file_progress_widgets, log_label = create_progress_dialog(parent, len(files_to_download))
            
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
                            
                            # Update log
                            log_label.configure(text=f"Downloading {file_name}... {downloaded / (1024*1024):.2f} MB / {total / (1024*1024):.2f} MB")
                            
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
                            
                            # Update log
                            log_label.configure(text=f"Downloaded {file_name}")
                        
                        elif status == "error":
                            file_name, component_type, error_message = data
                            
                            # Update file progress widget
                            if file_name in file_progress_widgets:
                                _, file_label, file_progress_bar = file_progress_widgets[file_name]
                                file_label.configure(text=f"{file_name} ({component_type}) - Error: {error_message}")
                            
                            # Add to download errors
                            download_errors.append(f"Error downloading {file_name} ({component_type}): {error_message}")
                            
                            # Update log
                            log_label.configure(text=f"Error downloading {file_name}: {error_message}")
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
                # Instead of closing completely, minimize to a small floating window
                dialog_closed[0] = True
                
                try:
                    # Hide the main dialog
                    progress_dialog.withdraw()
                    
                    # Create a small floating window to show progress
                    float_window = ctk.CTkToplevel()
                    float_window.title("Downloads in Progress")
                    float_window.geometry("300x120")
                    float_window.resizable(False, False)
                    float_window.attributes("-topmost", True)
                    float_window.focus_force()
                    
                    # Store reference to the window
                    float_windows[0] = float_window
                    
                    # Position in bottom right corner
                    screen_width = parent.winfo_screenwidth()
                    screen_height = parent.winfo_screenheight()
                    x = screen_width - 320
                    y = screen_height - 140
                    float_window.geometry(f"+{x}+{y}")
                    
                    # Add a label showing download status
                    status_label = ctk.CTkLabel(
                        float_window,
                        text=f"Downloading: {completed_files}/{len(files_to_download)} files",
                        font=("Helvetica", 12)
                    )
                    status_label.pack(pady=(15, 5), padx=10)
                    
                    # Add a small progress bar
                    mini_progress = ctk.CTkProgressBar(float_window, width=280)
                    mini_progress.pack(pady=(0, 15), padx=10)
                    
                    # Initialize progress bar with current progress
                    current_downloaded = sum(d for d, _ in file_progress.values())
                    current_total = sum(t for _, t in file_progress.values() if t > 0)
                    
                    if current_total > 0:
                        mini_progress.set(current_downloaded / current_total)
                    else:
                        mini_progress.set(completed_files / len(files_to_download) if len(files_to_download) > 0 else 0)
                    
                    # Add close handler for the floating window - use a lambda to ensure it's called correctly
                    float_window.protocol("WM_DELETE_WINDOW", lambda: cancel_downloads())
                    
                    # Create a function to process the download queue specifically for the mini window
                    def process_mini_download_queue():
                        nonlocal completed_files, downloaded_bytes, total_bytes
                        
                        # Check if downloads were cancelled
                        if downloads_cancelled[0]:
                            return
                        
                        # Check if window still exists
                        try:
                            if not float_window.winfo_exists():
                                return
                        except:
                            return
                        
                        # Process a limited number of items from the queue to keep UI responsive
                        queue_items_processed = 0
                        max_items_per_cycle = 10
                        
                        while not download_queue.empty() and queue_items_processed < max_items_per_cycle:
                            try:
                                status, data = download_queue.get_nowait()
                                queue_items_processed += 1
                                
                                if status == "progress":
                                    # Update file progress
                                    file_name, component_type, downloaded, total = data
                                    file_progress[file_name] = (downloaded, total)
                                
                                elif status == "complete":
                                    # Update completed files count
                                    file_name, component_type = data
                                    completed_files += 1
                            except:
                                pass
                        
                        # Recalculate the current progress values
                        current_downloaded = sum(d for d, _ in file_progress.values())
                        current_total = sum(t for _, t in file_progress.values() if t > 0)
                        
                        # Update status label with current values and percentage
                        if current_total > 0:
                            percentage = current_downloaded / current_total * 100
                            status_label.configure(text=f"Downloading: {completed_files}/{len(files_to_download)} files ({percentage:.1f}%)")
                        else:
                            status_label.configure(text=f"Downloading: {completed_files}/{len(files_to_download)} files")
                        
                        # Update progress bar with current progress
                        if current_total > 0:
                            progress_value = current_downloaded / current_total
                            mini_progress.set(progress_value)
                        else:
                            # Use file count as fallback if bytes not available
                            progress_value = completed_files / len(files_to_download) if len(files_to_download) > 0 else 0
                            mini_progress.set(progress_value)
                        
                        # Check if all downloads are complete
                        if completed_files >= len(files_to_download):
                            try:
                                float_window.destroy()
                            except:
                                pass
                            
                            # Show success or error message
                            if download_errors:
                                error_message = "\n".join(download_errors)
                                parent.after_idle(lambda: self._show_error(f"Some files failed to download:\n{error_message}"))
                            else:
                                parent.after_idle(lambda: self._show_success("All files downloaded successfully"))
                        else:
                            # Schedule the next queue processing
                            if not downloads_cancelled[0]:
                                float_window.after(100, process_mini_download_queue)
                    
                    # Start processing the download queue for the mini window
                    process_mini_download_queue()
                    
                    # Update the mini progress window periodically
                    def update_mini_progress():
                        nonlocal downloaded_bytes, total_bytes, completed_files
                        
                        # First check if downloads were cancelled
                        if downloads_cancelled[0]:
                            return
                            
                        # Then check if window still exists
                        try:
                            if not float_window.winfo_exists():
                                return
                        except:
                            return
                        
                        try:
                            # Recalculate the current progress values to ensure they're up-to-date
                            current_downloaded = 0
                            current_total = 0
                            
                            # Calculate progress for each file
                            for fname, (downloaded, total) in file_progress.items():
                                current_downloaded += downloaded
                                if total > 0:
                                    current_total += total
                            
                            # Schedule next update - only if not cancelled
                            if not downloads_cancelled[0]:
                                try:
                                    float_window.after(1000, update_mini_progress)
                                except:
                                    pass
                        except Exception as e:
                            # Only print actual errors, not debug info
                            print(f"Error updating mini progress: {e}")
                    
                    # Start updating mini progress
                    update_mini_progress()
                except Exception as e:
                    print(f"Error creating floating window: {e}")
            
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
        
        # Use the parent if provided, otherwise use self.parent_window, or create a new root
        parent = parent or self.parent_window
        
        # Format the list of existing files
        files_str = "\n".join(existing_files)
        
        if parent:
            # Create a dialog
            result = [False]  # Use a list to store the result (to be modified by inner functions)
            
            dialog = ctk.CTkToplevel(parent)
            dialog.title(f"Existing {component_type} Files Found")
            dialog.geometry("500x350")
            dialog.transient(parent)
            dialog.grab_set()
            dialog.attributes("-topmost", True)
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
            files_frame = ctk.CTkScrollableFrame(dialog, width=450, height=150)
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
                width=150,
                fg_color="#555555",
                hover_color="#333333"
            ).pack(side="left", padx=10)
            
            ctk.CTkButton(
                button_frame,
                text="Yes, Download Again",
                command=on_yes,
                width=150
            ).pack(side="right", padx=10)
            
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