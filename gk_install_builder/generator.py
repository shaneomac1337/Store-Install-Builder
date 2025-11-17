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
    from gk_install_builder.detection import DetectionManager
except ImportError:
    from detection import DetectionManager

try:
    from .gen_config import TEMPLATE_DIR, HELPER_STRUCTURE, DEFAULT_DOWNLOAD_WORKERS, DEFAULT_CHUNK_SIZE, LAUNCHER_TEMPLATES
    from .utils import create_directory_structure, copy_certificate, write_installation_script, determine_gk_install_paths, replace_urls_in_json, create_helper_structure, setup_firebird_environment_variables, get_component_version
    from .generators import (
        replace_hostname_regex_powershell,
        replace_hostname_regex_bash,
        generate_launcher_templates,
        create_default_template,
        generate_onboarding_script,
        generate_gk_install,
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
    from generators.gk_install_generator import generate_gk_install
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
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return generate_gk_install(
            output_dir, config, self.detection_manager,
            replace_hostname_regex_powershell, replace_hostname_regex_bash,
            script_dir
        )

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
            # Convert to absolute path if it's relative
            output_dir = os.path.abspath(output_dir)
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
            print(f"Output dir (absolute): {output_dir}")
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
                files_to_download, dialog_parent, self.parent_window
            )
            process_component(
                "WDM", "WDM", "wdm", "CSE-wdm",
                selected_components, output_dir, config, self.get_component_version,
                self.dsg_api_browser, prompt_for_file_selection,
                files_to_download, dialog_parent, self.parent_window
            )
            process_component(
                "FLOW-SERVICE", "FLOW-SERVICE", "flow_service", "GKR-FLOWSERVICE-CLOUD",
                selected_components, output_dir, config, self.get_component_version,
                self.dsg_api_browser, prompt_for_file_selection,
                files_to_download, dialog_parent, self.parent_window,
                display_name="Flow Service"
            )
            process_component(
                "LPA", "LPA-SERVICE", "lpa_service", "CSE-lps-lpa",
                selected_components, output_dir, config, self.get_component_version,
                self.dsg_api_browser, prompt_for_file_selection,
                files_to_download, dialog_parent, self.parent_window,
                display_name="LPA Service"
            )
            process_component(
                "SH", "STOREHUB-SERVICE", "storehub_service", "CSE-sh-cloud",
                selected_components, output_dir, config, self.get_component_version,
                self.dsg_api_browser, prompt_for_file_selection,
                files_to_download, dialog_parent, self.parent_window,
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
