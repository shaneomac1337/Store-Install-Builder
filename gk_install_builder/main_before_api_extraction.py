import customtkinter as ctk
from config import ConfigManager
from generator import ProjectGenerator
import os
import tkinter.ttk as ttk
import tkinter as tk
from tkinter import messagebox
import sys
import os
import requests
import json
from detection import DetectionManager
from environment_manager import EnvironmentManager
# Add parent directory to path to import PleasantPasswordClient
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pleasant_password_client import PleasantPasswordClient

# Import refactored modules
from ui.helpers import bind_mousewheel_to_frame
from utils.tooltips import create_tooltip
from utils.ui_colors import get_theme_colors
from dialogs.about import AboutDialog
from dialogs.launcher_settings import LauncherSettingsEditor
from dialogs.offline_package import OfflinePackageCreator
from dialogs.detection_settings import DetectionSettingsDialog
from features.auto_fill import AutoFillManager
from features.platform_handler import PlatformHandler

class GKInstallBuilder:
    # Class variables to store KeePass client and credentials
    keepass_client = None
    keepass_credentials = {}
    keepass_username = None
    keepass_password = None
    
    def __init__(self, root=None):
        # Set up customtkinter
        ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
        ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"
        
        # Create the main window if not provided
        if root is None:
            self.root = ctk.CTk()
            self.root.title("GK Install Builder")
            self.root.geometry("1280x1076")
        else:
            self.root = root
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
        # Initialize config manager
        self.config_manager = ConfigManager()
        
        # Ensure auth_service_ba_user is always set to "launchpad"
        self.config_manager.config["auth_service_ba_user"] = "launchpad"
        
        # Initialize project generator
        self.project_generator = ProjectGenerator(self.root)
        
        # Initialize the detection manager for file detection
        self.detection_manager = DetectionManager()
        
        # Load detection config if it exists in the main config
        if "detection_config" in self.config_manager.config:
            self.detection_manager.set_config(self.config_manager.config["detection_config"])
        
        # Initialize file detection window to None
        self.detection_window = None
        
        # Initialize parent_app to None (for window close handler)
        self.parent_app = None
        
        # Initialize offline creator to None
        self.offline_creator = None
        
        # Initialize password visibility tracking dictionary
        self.password_visible = {}
        
        # Initialize section frames dictionary
        self.section_frames = {}
        
        # Track whether this is first run (no config file)
        self.is_first_run = not os.path.exists(self.config_manager.config_file)
        platform = self.config_manager.config.get("platform", "Windows")
        # Only set platform-specific defaults if NOT first run
        if not self.is_first_run:
            if platform == "Windows":
                if not self.config_manager.config.get("base_install_dir") or "/" in self.config_manager.config.get("base_install_dir", ""):
                    self.config_manager.config["base_install_dir"] = "C:\\gkretail"
                self.config_manager.config["firebird_server_path"] = "C:\\Program Files\\Firebird\\Firebird_3_0"
                self.config_manager.config["firebird_driver_path_local"] = "C:\\gkretail\\Jaybird"
            else:  # Linux
                if not self.config_manager.config.get("base_install_dir") or "\\" in self.config_manager.config.get("base_install_dir", ""):
                    self.config_manager.config["base_install_dir"] = "/usr/local/gkretail"
                self.config_manager.config["firebird_server_path"] = "/opt/firebird"
                self.config_manager.config["firebird_driver_path_local"] = "/usr/local/gkretail/Jaybird"
        
        # Store section frames for progressive disclosure
        self.section_frames = {}
        
        # Initialize KeePass variables
        self.keepass_client = GKInstallBuilder.keepass_client
        self.keepass_username = GKInstallBuilder.keepass_username
        self.keepass_password = GKInstallBuilder.keepass_password
        
        # Create launcher settings editor
        self.launcher_editor = LauncherSettingsEditor(self.root, self.config_manager, self.project_generator)

        # Create environment manager
        self.environment_manager = EnvironmentManager(self.root, self.config_manager, self)

        # Initialize refactored feature modules
        self.auto_fill_manager = AutoFillManager(self.config_manager)
        self.platform_handler = PlatformHandler(self.config_manager)
        
        # Create the GUI
        self.create_gui()
        
        # Auto-fill based on URL if available
        base_url = self.config_manager.config.get("base_url", "")
        if base_url:
            print(f"Initial base URL from config: {base_url}")
            self.auto_fill_based_on_url(base_url)
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
        # Register the platform variable with config manager
        self.config_manager.register_entry("platform", self.platform_var)
        
        # On first run, ensure base install dir matches selected platform
        if self.is_first_run:
            self.on_platform_changed()
    
    def create_gui(self):
        # Create main container with scrollbar
        self.main_frame = ctk.CTkScrollableFrame(self.root, width=900, height=700)
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Apply mousewheel binding for Linux scrolling
        bind_mousewheel_to_frame(self.main_frame)
        
        # Add version/info label at the top right of the main frame
        info_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        info_frame.pack(fill="x", pady=(0, 10))
        
        # Info button styled to match customtkinter aesthetics
        info_button = ctk.CTkButton(
            info_frame,
            text="ⓘ",
            width=30,
            height=30,
            corner_radius=15,
            fg_color="transparent",
            hover_color=("gray75", "gray30"),
            text_color=("gray50", "gray70"),
            font=("Helvetica", 16),
            command=self.show_author_info
        )
        info_button.pack(side="right", padx=(0, 5))
        
        # Version label with customtkinter styling
        version_label = ctk.CTkLabel(
            info_frame,
            text="v5.27",
            font=("Helvetica", 12),
            text_color=("gray50", "gray70")
        )
        version_label.pack(side="right", padx=5)
        
        # Add tooltip to the info button
        self.create_tooltip(info_button, "About Store Install Builder")
        
        # Project Configuration - Create the main section frame
        section_frame = ctk.CTkFrame(self.main_frame)
        section_frame.pack(fill="x", padx=10, pady=(0, 20))
        
        # Store reference to section frame
        self.section_frames["Project Configuration"] = section_frame
        
        # Title
        ctk.CTkLabel(
            section_frame, 
            text="Project Configuration", 
            font=("Helvetica", 16, "bold")
        ).pack(anchor="w", padx=10, pady=10)
        
        # Create a frame for form fields
        form_frame = ctk.CTkFrame(section_frame)
        form_frame.pack(fill="x", padx=10, pady=5)
        
        # Add standard project configuration fields
        fields = ["Project Name", "Base URL", "Version"]
        
        # Field tooltips
        tooltips = {
            "Project Name": "Name of your project (e.g., 'Coop Sweden')",
            "Base URL": "Base URL for the cloud4retail environment (e.g., 'test.cse.cloud4retail.co')",
            "Version": "Version number of the installation (e.g., 'v1.2.0')",
        }
        
        # Create fields
        for field in fields:
            field_frame = ctk.CTkFrame(form_frame)
            field_frame.pack(fill="x", padx=10, pady=5)
            
            # Label with tooltip
            label = ctk.CTkLabel(
                field_frame, 
                text=f"{field}:",
                width=150
            )
            label.pack(side="left", padx=10)
            
            # Create tooltip for the label
            if field in tooltips:
                self.create_tooltip(label, tooltips[field])
            
            # Create the entry field
            config_key = field.lower().replace(" ", "_")
            entry = ctk.CTkEntry(field_frame, width=400)
            entry.pack(side="left", fill="x", expand=True, padx=10)
            
            # Set default value if available
            if config_key in self.config_manager.config:
                entry.insert(0, self.config_manager.config[config_key])
            
            # Register entry with config manager
            self.config_manager.register_entry(config_key, entry)

            # Special handling for main project version field
            if config_key == "version":
                # Bind to auto-update component versions on multiple events
                entry.bind("<KeyRelease>", lambda event: self.on_project_version_change())
                entry.bind("<FocusOut>", lambda event: self.on_project_version_change())
                entry.bind("<Return>", lambda event: self.on_project_version_change())
                # Also bind to paste events
                entry.bind("<Control-v>", lambda event: self.root.after(10, self.on_project_version_change))
        
        # Add Platform Selection
        platform_frame = ctk.CTkFrame(form_frame)
        platform_frame.pack(fill="x", padx=10, pady=5)
        
        platform_label = ctk.CTkLabel(platform_frame, text="Platform:", width=150)
        platform_label.pack(side="left", padx=10)
        
        # Create tooltip for platform
        self.create_tooltip(platform_label, "Select target platform for installation scripts")
        
        # Create a StringVar for the platform option
        self.platform_var = ctk.StringVar(value=self.config_manager.config.get("platform", "Windows"))
        
        # Create radio button frame
        radio_frame = ctk.CTkFrame(platform_frame)
        radio_frame.pack(side="left", padx=10)
        
        windows_radio = ctk.CTkRadioButton(
            radio_frame, 
            text="Windows", 
            variable=self.platform_var, 
            value="Windows",
            command=self.on_platform_changed
        )
        windows_radio.pack(side="left", padx=10)
        
        linux_radio = ctk.CTkRadioButton(
            radio_frame, 
            text="Linux", 
            variable=self.platform_var, 
            value="Linux",
            command=self.on_platform_changed
        )
        linux_radio.pack(side="left", padx=10)
        
        # Register the platform variable with config manager
        self.config_manager.register_entry("platform", self.platform_var)
        
        # Add Hostname Detection Toggle
        hostname_detection_frame = ctk.CTkFrame(form_frame)
        hostname_detection_frame.pack(fill="x", padx=10, pady=5)
        
        hostname_detection_label = ctk.CTkLabel(
            hostname_detection_frame, 
            text="Station Detection:",
            width=120
        )
        hostname_detection_label.pack(side="left", padx=10)
        
        # Create tooltip for hostname detection
        self.create_tooltip(hostname_detection_label, "Controls whether installation scripts will attempt to extract store ID and workstation ID from the computer hostname")
        
        # Create BooleanVars for the detection options
        self.hostname_detection_var = ctk.BooleanVar(value=self.config_manager.config.get("use_hostname_detection", True))
        self.file_detection_var = ctk.BooleanVar(value=self.config_manager.config.get("file_detection_enabled", True))

        # Create checkbox for hostname detection
        hostname_detection_checkbox = ctk.CTkCheckBox(
            hostname_detection_frame, 
            text="Enable automatic hostname detection",
            variable=self.hostname_detection_var,
            onvalue=True,
            offvalue=False,
            command=self.on_hostname_detection_changed
        )
        hostname_detection_checkbox.pack(side="left", padx=10)
        self.create_tooltip(hostname_detection_checkbox,
            "When enabled, the installation script will try to extract store ID and workstation ID from the computer hostname.\n"
            "When disabled, the script will skip hostname detection and use file detection or manual input instead.")

        # Create checkbox for file detection
        file_detection_checkbox = ctk.CTkCheckBox(
            hostname_detection_frame,
            text="Enable file detection",
            variable=self.file_detection_var,
            onvalue=True,
            offvalue=False,
            command=self.on_file_detection_changed
        )
        file_detection_checkbox.pack(side="left", padx=10)
        self.create_tooltip(file_detection_checkbox,
            "When enabled, the installation script will try to extract store ID and workstation ID from station files on disk.\n"
            "When disabled, file detection will not be attempted as a fallback.")

        # Register both detection variables with config manager
        self.config_manager.register_entry("use_hostname_detection", self.hostname_detection_var)
        self.config_manager.register_entry("file_detection_enabled", self.file_detection_var)
        
        # Add an information label to explain the fallback behavior


        
        # Add Detection Settings button
        detection_settings_btn = ctk.CTkButton(
            hostname_detection_frame,
            text="Detection Settings",
            width=150,
            command=self.open_detection_settings
        )
        detection_settings_btn.pack(side="left", padx=20)
        
        # Replace tooltip for detection settings button with robust logic
        class _DetectionButtonToolTip:
            def __init__(self, widget, text, delay=500):
                self.widget = widget
                self.text = text
                self.delay = delay
                self.tipwindow = None
                self.id = None
                self.widget.bind("<Enter>", self.schedule)
                self.widget.bind("<Leave>", self.unschedule)
                self.widget.bind("<ButtonPress>", self.unschedule)
                self.widget.bind("<Destroy>", self.cleanup)
            def schedule(self, event=None):
                self.unschedule()
                self.id = self.widget.after(self.delay, self.show)
            def unschedule(self, event=None):
                if self.id:
                    self.widget.after_cancel(self.id)
                    self.id = None
                self.hide()
            def show(self):
                if self.tipwindow or not self.text:
                    return
                x = self.widget.winfo_rootx() + 20
                y = self.widget.winfo_rooty() + 20
                self.tipwindow = tw = ctk.CTkToplevel(self.widget)
                tw.wm_overrideredirect(True)
                tw.wm_geometry(f"+{x}+{y}")
                label = ctk.CTkLabel(tw, text=self.text, fg_color="grey", text_color="white", corner_radius=4)
                label.pack(ipadx=4, ipady=2)
            def hide(self):
                if self.tipwindow:
                    self.tipwindow.destroy()
                    self.tipwindow = None
            def cleanup(self, event=None):
                self.unschedule()
                self.widget = None
        _DetectionButtonToolTip(
            detection_settings_btn,
            "Configure file detection settings and hostname regex patterns\nFile detection serves as a fallback when hostname detection fails or is disabled"
        )
        
        # Add validation and auto-fill for Base URL
        base_url_entry = self.config_manager.get_entry("base_url")
        if base_url_entry:
            base_url_entry.bind("<FocusOut>", self.on_base_url_changed)
        
        # Add Environment Manager button
        env_manager_frame = ctk.CTkFrame(form_frame)
        env_manager_frame.pack(fill="x", padx=10, pady=10)
        
        env_manager_label = ctk.CTkLabel(
            env_manager_frame,
            text="Multi-Environment:",
            width=150
        )
        env_manager_label.pack(side="left", padx=10)
        
        env_manager_btn = ctk.CTkButton(
            env_manager_frame,
            text="Manage Environments (Multi-Tenancy)",
            width=300,
            command=self.open_environment_manager,
            fg_color="#2b5f8f",
            hover_color="#1a4060"
        )
        env_manager_btn.pack(side="left", padx=10)
        
        self.create_tooltip(
            env_manager_btn,
            "Configure multiple environments with different credentials and settings.\n"
            "Scripts will automatically detect the correct environment based on CLI parameter,\n"
            "hostname detection, or file detection. Perfect for multi-tenant deployments!"
        )
        
        # Only create other sections if not first run
        if not self.is_first_run:
            self.create_remaining_sections()
        else:
            # Add a "Continue" button after Project Configuration
            self.continue_frame = ctk.CTkFrame(self.main_frame)
            self.continue_frame.pack(fill="x", padx=10, pady=10)
            
            continue_btn = ctk.CTkButton(
                self.continue_frame,
                text="Continue",
                width=200,
                command=self.on_continue
            )
            continue_btn.pack(anchor="center", padx=10, pady=10)
    
    def create_remaining_sections(self):
        # Remove continue button if it exists
        if hasattr(self, 'continue_frame'):
            self.continue_frame.destroy()
            
        # Component-specific versions
        if "Component Versions" not in self.section_frames:
            self.create_component_versions()
        
        # Installation Configuration
        if "Installation Configuration" not in self.section_frames:
            # Create the main section frame
            section_frame = ctk.CTkFrame(self.main_frame)
            section_frame.pack(fill="x", padx=10, pady=(0, 20))
            
            # Store reference to section frame
            self.section_frames["Installation Configuration"] = section_frame
            
            # Title
            ctk.CTkLabel(
                section_frame, 
                text="Installation Configuration", 
                font=("Helvetica", 16, "bold")
            ).pack(anchor="w", padx=10, pady=10)
            
            # Create a frame for form fields
            form_frame = ctk.CTkFrame(section_frame)
            form_frame.pack(fill="x", padx=10, pady=5)
            
            # Add the standard installation configuration fields
            fields = [
                "Base Install Directory",
                "Tenant ID",
                "POS System Type",
                "WDM System Type",
                "Flow Service System Type",
                "LPA Service System Type",
                "StoreHub Service System Type",
                "Firebird Server Path"
            ]
            
            # Field tooltips for this section
            tooltips = {
                "Base Install Directory": "Root directory where components will be installed (e.g., 'C:\\gkretail' for Windows or '/usr/local/gkretail' for Linux)",
                "Tenant ID": "Tenant identifier for multi-tenant environments (e.g., '001')",
                "POS System Type": "Type of Point of Sale system (e.g., 'CSE-OPOS-CLOUD')",
                "Flow Service System Type": "Type of Flow Service (e.g., 'CSE-FlowService')",
                "LPA Service System Type": "Type of LPA Service (e.g., 'CSE-LPA-Service')",
                "StoreHub Service System Type": "Type of StoreHub Service (e.g., 'CSE-StoreHub-Service')",
                "WDM System Type": "Type of Wall Device Manager (e.g., 'CSE-wdm')",
                "Firebird Server Path": "Path to the Firebird server (e.g., '/opt/firebird')",
            }
            
            # Create fields
            for field in fields:
                field_frame = ctk.CTkFrame(form_frame)
                field_frame.pack(fill="x", padx=10, pady=5)
                
                # Label with tooltip
                label = ctk.CTkLabel(
                    field_frame, 
                    text=f"{field}:",
                    width=150
                )
                label.pack(side="left", padx=10)
                
                # Create tooltip for the label
                if field in tooltips:
                    self.create_tooltip(label, tooltips[field])
                
                # Special case for Base Install Directory - use base_install_dir instead of base_install_directory
                if field == "Base Install Directory":
                    config_key = "base_install_dir"
                else:
                    config_key = field.lower().replace(" ", "_")
                
                # Create entry
                entry = ctk.CTkEntry(field_frame, width=400)
                entry.pack(side="left", fill="x", expand=True, padx=10)
                
                # Set default value
                if config_key in self.config_manager.config:
                    entry.insert(0, self.config_manager.config[config_key])
                
                # Register entry with config manager
                self.config_manager.register_entry(config_key, entry)
            
            # Ensure base install directory is set
            base_dir_entry = self.config_manager.get_entry("base_install_dir")
            firebird_path_entry = self.config_manager.get_entry("firebird_server_path")
            
            if base_dir_entry or firebird_path_entry:
                platform = self.platform_var.get()
                
                # Set platform-specific directories
                if platform == "Linux":
                    default_dir = "/usr/local/gkretail"
                    default_firebird = "/opt/firebird"
                else:  # Windows
                    default_dir = "C:\\gkretail"
                    default_firebird = "C:\\Program Files\\Firebird\\Firebird_3_0"
                
                # Update base directory if needed
                if base_dir_entry:
                    current_value = base_dir_entry.get()
                    if not current_value or (platform == "Linux" and "\\" in current_value) or (platform == "Windows" and "/" in current_value):
                        base_dir_entry.delete(0, 'end')
                        base_dir_entry.insert(0, default_dir)
                        print(f"Set base install directory to {default_dir} in create_remaining_sections")
                
                # Update Firebird path if needed
                if firebird_path_entry:
                    current_firebird = firebird_path_entry.get()
                    if not current_firebird or (platform == "Linux" and "\\" in current_firebird) or (platform == "Windows" and "/" in current_firebird):
                        firebird_path_entry.delete(0, 'end')
                        firebird_path_entry.insert(0, default_firebird)
                        print(f"Set Firebird server path to {default_firebird} in create_remaining_sections")
        
        # Security Configuration
        if "Security Configuration" not in self.section_frames:
            fields = [
                "EH/Launchpad Username",
                "EH/Launchpad Password",
                "Auth Service BA User",
                "Launchpad OAuth2",
                "SSL Password"
            ]
            self.create_section("Security Configuration", fields)
        
        # Output Directory
        if not hasattr(self, 'output_dir_entry'):
            self.create_output_selection()
        
        # Status label for auto-save
        if not hasattr(self, 'save_status_label'):
            self.create_status_label()
        
        # Buttons
        if not hasattr(self, 'buttons_created'):
            self.create_buttons()
            self.buttons_created = True
            
        # Ensure fields are populated with auto-fill values
        base_url = self.config_manager.config.get("base_url", "")
        if base_url:
            print(f"Re-applying auto-fill with base URL: {base_url}")
            self.auto_fill_based_on_url(base_url)
            
            # Force update of specific fields
            for key in ["pos_system_type", "wdm_system_type", "base_install_dir"]:
                value = self.config_manager.config.get(key, "")
                if key == "base_install_dir" and not value:
                    platform = self.platform_var.get() if hasattr(self, 'platform_var') else "Windows"
                    value = "/usr/local/gkretail" if platform == "Linux" else "C:\\gkretail"
                    self.config_manager.config[key] = value
                
                entry = self.config_manager.get_entry(key)
                if entry and value:
                    entry.delete(0, 'end')
                    entry.insert(0, value)
                    print(f"Force updated {key} to: {value}")
    
    def on_continue(self):
        """Handle continue button click"""
        # Validate required fields
        project_name = self.config_manager.get_entry("project_name").get()
        base_url = self.config_manager.get_entry("base_url").get()
        version = self.config_manager.get_entry("version").get()
        
        if not project_name or not base_url:
            messagebox.showwarning("Required Fields", "Please fill in Project Name and Base URL before continuing.")
            return
        
        # Set default version if empty
        if not version:
            self.config_manager.update_entry_value("version", "v1.0.0")
        
        print(f"Continue clicked with base URL: {base_url}")
        
        # Auto-fill fields based on base URL
        self.auto_fill_based_on_url(base_url)
        
        # Ensure base install directory is set
        platform = self.platform_var.get() if hasattr(self, 'platform_var') else "Windows"
        default_dir = "/usr/local/gkretail" if platform == "Linux" else "C:\\gkretail"
        self.config_manager.config["base_install_dir"] = default_dir
        print(f"Setting default base install directory to {default_dir} in on_continue")
        
        # Save current configuration
        self.config_manager.update_config_from_entries()
        self.config_manager.save_config_silent()
        
        # Create remaining sections - this will create the fields that will be auto-filled
        self.create_remaining_sections()
        
        # Force update of the entries with the values from config
        # This ensures the GUI displays the auto-filled values
        for key, value in self.config_manager.config.items():
            entry = self.config_manager.get_entry(key)
            if entry and hasattr(entry, "delete") and hasattr(entry, "insert"):
                # Only update if the entry exists and is empty
                if not entry.get():
                    entry.delete(0, 'end')
                    entry.insert(0, value)
                    print(f"Updated entry {key} with value {value}")
        
        # Specifically ensure POS and WDM system types are updated
        pos_type = self.config_manager.config.get("pos_system_type", "")
        wdm_type = self.config_manager.config.get("wdm_system_type", "")
        base_install_dir = self.config_manager.config.get("base_install_dir", "C:\\gkretail")
        
        pos_entry = self.config_manager.get_entry("pos_system_type")
        wdm_entry = self.config_manager.get_entry("wdm_system_type")
        base_dir_entry = self.config_manager.get_entry("base_install_dir")
        
        if pos_entry and pos_type:
            pos_entry.delete(0, 'end')
            pos_entry.insert(0, pos_type)
            print(f"Force updated POS system type to: {pos_type}")
            
        if wdm_entry and wdm_type:
            wdm_entry.delete(0, 'end')
            wdm_entry.insert(0, wdm_type)
            print(f"Force updated WDM system type to: {wdm_type}")
            
        if base_dir_entry:
            base_dir_entry.delete(0, 'end')
            base_dir_entry.insert(0, base_install_dir)
            print(f"Force updated base install directory to: {base_install_dir}")
    
    def on_base_url_changed(self, event):
        """Handle base URL field changes"""
        base_url = event.widget.get()
        if base_url:
            # Auto-suggest values based on URL - always do this, not just on first run
            self.auto_fill_based_on_url(base_url)
            
            # Ensure the output directory field is updated
            if hasattr(self, 'output_dir_entry'):
                # Extract project name from URL if needed
                extracted_project_name = ""
                if "." in base_url:
                    parts = base_url.split(".")
                    if len(parts) > 1:
                        extracted_project_name = parts[1].upper()
                
                # Get project name (from entry or extracted)
                project_name = self.config_manager.get_entry("project_name").get() if self.config_manager.get_entry("project_name") else extracted_project_name
                
                if project_name:
                    # Set the output directory
                    output_dir = os.path.join(project_name, base_url)
                    self.output_dir_entry.configure(state="normal")
                    self.output_dir_entry.delete(0, 'end')
                    self.output_dir_entry.insert(0, output_dir)
                    self.config_manager.config["output_dir"] = output_dir
                    self.config_manager.save_config_silent()
                    print(f"Updated output directory to: {output_dir}")
    
    def auto_fill_based_on_url(self, base_url):
        """Auto-fill fields based on the base URL (delegates to AutoFillManager)"""
        platform_var = self.platform_var if hasattr(self, 'platform_var') else None
        return self.auto_fill_manager.auto_fill_based_on_url(base_url, platform_var)
    
    def create_section(self, title, fields):
        # Section Frame
        section_frame = ctk.CTkFrame(self.main_frame)
        section_frame.pack(fill="x", pady=10, padx=20)
        
        # Store reference to the section frame
        self.section_frames[title] = section_frame
        
        # Section Title
        ctk.CTkLabel(
            section_frame,
            text=title,
            font=("Helvetica", 14, "bold")
        ).pack(pady=5)
        
        # Create fields
        for field in fields:
            # Create frame for this field
            field_frame = ctk.CTkFrame(section_frame)
            field_frame.pack(fill="x", pady=5, padx=10)
            
            # Create label
            ctk.CTkLabel(
                field_frame,
                text=field + ":",
                width=150
            ).pack(side="left")
            
            # Convert field name to config key
            config_key = field.lower().replace(" ", "_").replace("/", "_")
            
            # Create entry - use password field for password fields
            if "password" in field.lower() or field == "Launchpad OAuth2":
                # Create password field with show/hide toggle
                entry, _ = self.create_password_field(field_frame, field, config_key)
            elif field == "Auth Service BA User":
                # Create a read-only entry with fixed value "launchpad"
                entry = ctk.CTkEntry(field_frame, width=300)  # Changed width from 200 to 300
                entry.pack(side="left", padx=5)
                entry.insert(0, "launchpad")
                entry.configure(state="readonly")  # Make it read-only
                
                # Store the fixed value in the config
                self.config_manager.config[config_key] = "launchpad"
                
                # Register entry with config manager with a fixed value
                self.config_manager.register_entry(config_key, entry, fixed_value="launchpad")
                
                # Add tooltip to explain that this field is read-only
                self.create_tooltip(entry, "This field is read-only. 'launchpad' is the only supported value.")
            else:
                # Create regular entry with consistent width
                entry = ctk.CTkEntry(field_frame, width=300)  # Changed width from 200 to 300
                entry.pack(side="left", padx=5)
                
                # Load saved value if exists
                if config_key in self.config_manager.config:
                    entry.insert(0, self.config_manager.config[config_key])
            
            # Register entry with config manager
            self.config_manager.register_entry(config_key, entry)
            
            # Add KeePass button only for specific fields
            if field == "Launchpad OAuth2":
                self.basic_auth_password_entry = entry  # Store reference to this entry
                ctk.CTkButton(
                    field_frame,
                    text="🔑",  # Key icon
                    width=40,
                    command=lambda: self.get_basic_auth_password_from_keepass(password_type="basic_auth")
                ).pack(side="left", padx=5)
            elif field == "Webdav Admin":
                self.webdav_admin_password_entry = entry  # Store reference to this entry
                ctk.CTkButton(
                    field_frame,
                    text="🔑",  # Key icon
                    width=40,
                    command=lambda: self.get_basic_auth_password_from_keepass(password_type="webdav_admin")
                ).pack(side="left", padx=5)
            elif field == "EH/Launchpad Password":
                self.form_password_entry = entry  # Store reference to this entry
                # No KeePass button for Form Password
            elif field == "SSL Password":
                self.ssl_password_entry = entry  # Store reference to this entry
            elif field == "Base URL":
                # Add refresh icon button next to Base URL field
                refresh_button = ctk.CTkButton(
                    field_frame,
                    text="⟳",  # Alternative refresh symbol (larger and more visible)
                    width=40,
                    height=40,
                    font=("Helvetica", 20),  # Increase font size for the icon
                    command=self.regenerate_configuration
                )
                refresh_button.pack(side="left", padx=5)
                self.create_tooltip(refresh_button, "Regenerate configuration based on URL")
                
                # Bind the entry to the on_base_url_changed event
                entry.bind("<KeyRelease>", self.on_base_url_changed)
        
        # Add certificate management section if this is the Security Configuration section
        if title == "Security Configuration":
            self.create_certificate_section(section_frame)
        
        # Special handling for Installation Configuration section
        if title == "Installation Configuration":
            # Always ensure base_install_dir is set to C:\gkretail
            base_dir_entry = self.config_manager.get_entry("base_install_dir")
            print(f"Base install directory entry found: {base_dir_entry is not None}")
            
            if base_dir_entry:
                # Force update the entry
                current_value = base_dir_entry.get()
                print(f"Current base install directory value: '{current_value}'")
                
                # Always update regardless of current value
                base_dir_entry.delete(0, 'end')
                base_dir_entry.insert(0, "C:\\gkretail")
                print("Updated base install directory to: C:\\gkretail")
                
                # Also update the config
                self.config_manager.config["base_install_dir"] = "C:\\gkretail"
                print("Updated config base_install_dir to: C:\\gkretail")
            
            # Ensure POS and WDM system types are updated from config
            base_url = self.config_manager.config.get("base_url", "")
            if base_url:
                print(f"Updating system types based on URL: {base_url}")
                # Extract project name from URL
                if "." in base_url:
                    parts = base_url.split(".")
                    project_name = "GKR"  # Default project name
                    if len(parts) >= 2 and parts[1]:
                        project_name = parts[1].upper()
                    
                    # Set system types
                    pos_type = f"{project_name}-OPOS-CLOUD"
                    wdm_type = f"{project_name}-wdm"
                    
                    # Update entries
                    pos_entry = self.config_manager.get_entry("pos_system_type")
                    wdm_entry = self.config_manager.get_entry("wdm_system_type")
                    
                    # Always update these fields
                    if pos_entry:
                        pos_entry.delete(0, 'end')
                        pos_entry.insert(0, pos_type)
                        print(f"Updated POS system type to: {pos_type}")
                    
                    if wdm_entry:
                        wdm_entry.delete(0, 'end')
                        wdm_entry.insert(0, wdm_type)
                        print(f"Updated WDM system type to: {wdm_type}")
                    
                    # Update certificate path
                    cert_entry = self.config_manager.get_entry("certificate_path")
                    if cert_entry:
                        cert_entry.delete(0, 'end')
                        cert_entry.insert(0, "generated_scripts/certificate.p12")
                        print("Updated certificate path to: generated_scripts/certificate.p12")
    
    def create_password_field(self, parent_frame, field, config_key):
        """Create a password field with integrated show/hide toggle"""
        # Create a container frame to hold both entry and button
        container_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        container_frame.pack(side="left", padx=10, fill="x", expand=False)
        
        # Create the password entry with show=* for masking (reduced width)
        entry = ctk.CTkEntry(container_frame, width=300, show="*")  # Changed width from 200 to 300
        entry.pack(side="left", fill="x", expand=False)
        
        # Load saved value if exists
        if config_key in self.config_manager.config:
            entry.insert(0, self.config_manager.config[config_key])
        
        # Initialize visibility state for this field
        self.password_visible[field] = False
        
        # Button container to ensure consistent spacing and alignment
        button_container = ctk.CTkFrame(container_frame, fg_color="transparent")
        button_container.pack(side="left", padx=(2, 0))
        
        # Create toggle button with better appearance
        toggle_btn = ctk.CTkButton(
            button_container,
            text="👁",  # Use smaller eye icon
            width=28,
            height=28,
            corner_radius=5,
            fg_color="#2B2B2B",  # Dark background matching theme
            hover_color="#3E3E3E",  # Slightly lighter on hover
            border_width=0,
            command=lambda e=entry, f=field: self.toggle_password_visibility(e, f)
        )
        toggle_btn.pack(side="left", padx=2)
        
        # Define a focus event handler to clear placeholder text
        def clear_placeholder(event):
            if entry.get() == self.config_manager.config.get(config_key, ''):
                entry.delete(0, 'end')

        # Define a focus out event handler to restore placeholder text
        def restore_placeholder(event):
            if entry.get() == '':
                entry.insert(0, self.config_manager.config.get(config_key, ''))

        # Bind the focus in and focus out events to the handlers
        entry.bind('<FocusIn>', clear_placeholder)
        entry.bind('<FocusOut>', restore_placeholder)
        
        return entry, toggle_btn
        
    def toggle_password_visibility(self, entry, field):
        """Toggle password visibility between masked and plain text"""
        # Initialize the field in the dictionary if it doesn't exist
        if field not in self.password_visible:
            self.password_visible[field] = False
            
        # Toggle the state
        self.password_visible[field] = not self.password_visible[field]
        
        # Get current text
        current_text = entry.get()
        
        # Clear the entry
        entry.delete(0, 'end')
        
        # Update show parameter based on visibility state
        if self.password_visible[field]:
            entry.configure(show="")  # Show plain text
        else:
            entry.configure(show="*")  # Show masked text
        
        # Restore the text
        entry.insert(0, current_text)
    
    def create_certificate_section(self, parent_frame):
        """Create certificate management section"""
        # Certificate management frame
        cert_frame = ctk.CTkFrame(parent_frame)
        cert_frame.pack(fill="x", padx=10, pady=10)
        
        # Certificate path
        cert_path_frame = ctk.CTkFrame(cert_frame)
        cert_path_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            cert_path_frame,
            text="Certificate Path:",
            width=150
        ).pack(side="left", padx=10)
        
        self.cert_path_entry = ctk.CTkEntry(cert_path_frame, width=300)  # Changed from 200 to 300
        self.cert_path_entry.pack(side="left", padx=10)
        
        # Load saved value if exists
        if "certificate_path" in self.config_manager.config:
            self.cert_path_entry.insert(0, self.config_manager.config["certificate_path"])
        
        self.config_manager.register_entry("certificate_path", self.cert_path_entry)
        
        # Browse button
        ctk.CTkButton(
            cert_path_frame,
            text="Browse",
            width=80,
            command=self.browse_certificate_path
        ).pack(side="left", padx=5)
        
        # Certificate common name
        cert_common_name_frame = ctk.CTkFrame(cert_frame)
        cert_common_name_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            cert_common_name_frame,
            text="Common Name:",
            width=150
        ).pack(side="left", padx=10)
        
        self.cert_common_name_entry = ctk.CTkEntry(cert_common_name_frame, width=300)  # Changed from 200 to 300
        self.cert_common_name_entry.pack(side="left", padx=10)
        
        # Load saved value if exists
        if "certificate_common_name" in self.config_manager.config:
            self.cert_common_name_entry.insert(0, self.config_manager.config["certificate_common_name"])
        
        self.config_manager.register_entry("certificate_common_name", self.cert_common_name_entry)
        
        # Certificate status and buttons
        cert_status_frame = ctk.CTkFrame(cert_frame)
        cert_status_frame.pack(fill="x", padx=10, pady=5)
        
        # Status label
        self.cert_status_label = ctk.CTkLabel(
            cert_status_frame,
            text="",
            width=150
        )
        self.cert_status_label.pack(side="left", padx=10)
        
        # Generate button
        ctk.CTkButton(
            cert_status_frame,
            text="Generate Certificate",
            width=150,
            command=self.generate_certificate
        ).pack(side="left", padx=5)
        
        # Check certificate status
        self.check_certificate_status()
        
        # Add tooltip for certificate section
        self.create_tooltip(cert_frame, "SSL Certificate for secure communication. The certificate will be generated with the specified common name and will include a Subject Alternative Name (SAN) matching the common name.")
    
    def browse_certificate_path(self):
        """Browse for certificate path"""
        # Get initial directory from current path
        initial_dir = os.path.dirname(self.cert_path_entry.get())
        if not os.path.exists(initial_dir):
            initial_dir = "."
        
        # Ask for save path
        file_path = ctk.filedialog.asksaveasfilename(
            initialdir=initial_dir,
            title="Select Certificate Path",
            filetypes=[("PKCS#12 Files", "*.p12"), ("All Files", "*.*")],
            defaultextension=".p12"
        )
        
        if file_path:
            self.cert_path_entry.delete(0, "end")
            self.cert_path_entry.insert(0, file_path)
            self.check_certificate_status()
    
    def check_certificate_status(self):
        """Check if certificate exists and update status"""
        cert_path = self.cert_path_entry.get()
        
        if os.path.exists(cert_path):
            self.cert_status_label.configure(text="Certificate exists", text_color="green")
        else:
            self.cert_status_label.configure(text="No certificate found", text_color="orange")
    
    def generate_certificate(self):
        """Generate a self-signed certificate"""
        try:
            # Get certificate details
            cert_path = self.cert_path_entry.get()
            common_name = self.cert_common_name_entry.get()
            password = self.ssl_password_entry.get() if hasattr(self, 'ssl_password_entry') else "changeit"
            
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(cert_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"Created directory: {output_dir}")
            
            # Generate certificate using OpenSSL directly
            import subprocess
            import tempfile
            
            # Create a temporary OpenSSL config file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cnf') as temp:
                temp.write(f"""
                [req]
                distinguished_name = req_distinguished_name
                req_extensions = v3_req
                prompt = no
                
                [req_distinguished_name]
                C = DE
                ST = Saxony
                L = Dresden
                O = GK Software SE
                CN = {common_name}
                
                [v3_req]
                keyUsage = keyEncipherment, dataEncipherment
                extendedKeyUsage = serverAuth
                subjectAltName = @alt_names
                
                [alt_names]
                DNS.1 = {common_name}
                """)
                config_file = temp.name
            
            try:
                # Create temporary files for the cert and key
                with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_cert:
                    temp_cert_path = temp_cert.name
                
                with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_key:
                    temp_key_path = temp_key.name
                
                # Generate key
                subprocess.run(
                    f'openssl genrsa -out "{temp_key_path}" 2048',
                    shell=True, check=True
                )
                
                # Generate certificate
                subprocess.run(
                    f'openssl req -new -x509 -key "{temp_key_path}" -out "{temp_cert_path}" -days 3650 -config "{config_file}"',
                    shell=True, check=True
                )
                
                # Convert to PKCS12
                subprocess.run(
                    f'openssl pkcs12 -export -out "{cert_path}" -inkey "{temp_key_path}" -in "{temp_cert_path}" -password pass:{password}',
                    shell=True, check=True
                )
                
                # Clean up the temporary files
                os.unlink(config_file)
                os.unlink(temp_cert_path)
                os.unlink(temp_key_path)
                
                # Show success message
                self.cert_status_label.configure(text="Certificate generated", text_color="green")
                self.show_info("Certificate Generated", 
                              f"Certificate generated successfully at:\n{cert_path}\n\n"
                              f"Common Name: {common_name}\n"
                              f"Subject Alternative Name (SAN): {common_name}\n"
                              f"Valid for: 10 years")
                
                # Update certificate status
                self.check_certificate_status()
                
                return True
                
            except Exception as e2:
                # Clean up any temporary files
                try:
                    os.unlink(config_file)
                    os.unlink(temp_cert_path)
                    os.unlink(temp_key_path)
                except:
                    pass
                
                # Show error message
                self.cert_status_label.configure(text="Certificate generation failed", text_color="red")
                self.show_error("Certificate Generation Failed", f"Error: {str(e2)}")
                return False
                
        except Exception as e:
            self.cert_status_label.configure(text="Certificate generation failed", text_color="red")
            self.show_error("Certificate Generation Failed", f"Error: {str(e)}")
            return False
    
    def create_component_versions(self):
        # Create frame for component-specific versions
        component_frame = ctk.CTkFrame(self.main_frame)
        component_frame.pack(padx=10, pady=10, fill="x", expand=False)
        
        # Title
        title_label = ctk.CTkLabel(component_frame, text="Component-Specific Versions", font=("Arial", 14, "bold"))
        title_label.pack(padx=10, pady=(10, 5), anchor="w")
        
        # Description
        desc_label = ctk.CTkLabel(component_frame, text="Specify versions for different component types (leave empty to use project version)")
        desc_label.pack(padx=10, pady=(0, 10), anchor="w")
        
        # Create grid for version inputs
        grid_frame = ctk.CTkFrame(component_frame)
        grid_frame.pack(padx=10, pady=5, fill="x", expand=True)
        
        # Version override checkbox
        self.version_override_var = ctk.BooleanVar(value=self.config_manager.config.get("use_version_override", False))
        override_checkbox = ctk.CTkCheckBox(
            grid_frame,
            text="Enable Version Override",
            variable=self.version_override_var,
            command=self.toggle_version_override
        )
        override_checkbox.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.create_tooltip(override_checkbox, "Enable to specify custom versions for each component type")

        # Use Default Versions checkbox
        self.use_default_versions_var = ctk.BooleanVar(value=self.config_manager.config.get("use_default_versions", False))
        default_versions_checkbox = ctk.CTkCheckBox(
            grid_frame,
            text="Use Default Versions (fetch from API)",
            variable=self.use_default_versions_var,
            command=self.toggle_default_versions
        )
        default_versions_checkbox.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.create_tooltip(default_versions_checkbox, "When enabled, the installation script will fetch component versions from the selected API instead of using hardcoded versions")
        
        # Version source selection (FP/FPD vs Config-Service)
        version_source_label = ctk.CTkLabel(grid_frame, text="API Source:")
        version_source_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.version_source_var = ctk.StringVar(value=self.config_manager.config.get("default_version_source", "FP"))
        version_source_dropdown = ctk.CTkOptionMenu(
            grid_frame,
            variable=self.version_source_var,
            values=["FP", "CONFIG-SERVICE"],
            command=self.on_version_source_change,
            width=200
        )
        version_source_dropdown.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.create_tooltip(version_source_label, "Choose which API to use for fetching default versions")
        self.create_tooltip(version_source_dropdown, "FP = Function Pack (FP/FPD scope)\nCONFIG-SERVICE = Config-Service (versions/search)")
        self.config_manager.register_entry("default_version_source", self.version_source_var)

        # Test API button
        test_api_button = ctk.CTkButton(
            grid_frame,
            text="Test API",
            command=self.test_default_versions_api,
            width=100,
            height=28
        )
        test_api_button.grid(row=2, column=2, padx=10, pady=5, sticky="w")
        self.create_tooltip(test_api_button, "Test the selected API to verify it can fetch default component versions")
        
        # Get project version from config
        project_version = self.config_manager.config.get("version", "")
        
        # Store version field references for show/hide functionality
        self.version_fields = []

        # POS Version
        pos_label = ctk.CTkLabel(grid_frame, text="POS Version:")
        pos_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.pos_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.pos_version_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        self.pos_version_entry.insert(0, self.config_manager.config.get("pos_version", project_version))
        self.config_manager.register_entry("pos_version", self.pos_version_entry)
        self.create_tooltip(pos_label, "Version for POS components (applies to all POS system types)")
        self.create_tooltip(self.pos_version_entry, "Example: v1.0.0")
        self.version_fields.extend([pos_label, self.pos_version_entry])

        # WDM Version
        wdm_label = ctk.CTkLabel(grid_frame, text="WDM Version:")
        wdm_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.wdm_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.wdm_version_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.wdm_version_entry.insert(0, self.config_manager.config.get("wdm_version", project_version))
        self.config_manager.register_entry("wdm_version", self.wdm_version_entry)
        self.create_tooltip(wdm_label, "Version for WDM components (applies to all WDM system types)")
        self.create_tooltip(self.wdm_version_entry, "Example: v1.0.0")
        self.version_fields.extend([wdm_label, self.wdm_version_entry])

        # Flow Service Version
        flow_service_label = ctk.CTkLabel(grid_frame, text="Flow Service Version:")
        flow_service_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.flow_service_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.flow_service_version_entry.grid(row=5, column=1, padx=10, pady=5, sticky="w")
        self.flow_service_version_entry.insert(0, self.config_manager.config.get("flow_service_version", project_version))
        self.config_manager.register_entry("flow_service_version", self.flow_service_version_entry)
        self.create_tooltip(flow_service_label, "Version for Flow Service components")
        self.create_tooltip(self.flow_service_version_entry, "Example: v1.0.0")
        self.version_fields.extend([flow_service_label, self.flow_service_version_entry])

        # LPA Service Version
        lpa_service_label = ctk.CTkLabel(grid_frame, text="LPA Service Version:")
        lpa_service_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.lpa_service_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.lpa_service_version_entry.grid(row=6, column=1, padx=10, pady=5, sticky="w")
        self.lpa_service_version_entry.insert(0, self.config_manager.config.get("lpa_service_version", project_version))
        self.config_manager.register_entry("lpa_service_version", self.lpa_service_version_entry)
        self.create_tooltip(lpa_service_label, "Version for LPA Service components")
        self.create_tooltip(self.lpa_service_version_entry, "Example: v1.0.0")
        self.version_fields.extend([lpa_service_label, self.lpa_service_version_entry])

        # StoreHub Service Version
        storehub_service_label = ctk.CTkLabel(grid_frame, text="StoreHub Service Version:")
        storehub_service_label.grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.storehub_service_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.storehub_service_version_entry.grid(row=7, column=1, padx=10, pady=5, sticky="w")
        self.storehub_service_version_entry.insert(0, self.config_manager.config.get("storehub_service_version", project_version))
        self.version_fields.extend([storehub_service_label, self.storehub_service_version_entry])
        self.config_manager.register_entry("storehub_service_version", self.storehub_service_version_entry)
        self.create_tooltip(storehub_service_label, "Version for StoreHub Service components")
        self.create_tooltip(self.storehub_service_version_entry, "Example: v1.0.0")

        # Register the checkboxes with config manager
        self.config_manager.register_entry("use_version_override", self.version_override_var)
        self.config_manager.register_entry("use_default_versions", self.use_default_versions_var)
        
        # Initialize state based on config
        self.toggle_version_override()
    
    def toggle_version_override(self):
        """Toggle the enabled state of version fields based on checkbox"""
        enabled = self.version_override_var.get()
        state = "normal" if enabled else "disabled"

        # Mutual exclusion: disable default versions when version override is enabled
        if enabled and self.use_default_versions_var.get():
            self.use_default_versions_var.set(False)
            self.config_manager.config["use_default_versions"] = False
            print("Default versions disabled: Version override takes precedence")

        # Get project version
        project_version = self.config_manager.config.get("version", "")
        
        # Update entry states and values
        version_entries = [
            (self.pos_version_entry, "pos_version"),
            (self.wdm_version_entry, "wdm_version"),
            (self.flow_service_version_entry, "flow_service_version"),
            (self.lpa_service_version_entry, "lpa_service_version"),
            (self.storehub_service_version_entry, "storehub_service_version")
        ]
        
        for entry, config_key in version_entries:
            # Configure entry state
            entry.configure(state="normal")  # Temporarily enable to modify
            
            if not enabled:
                # If disabling override, reset to project version
                entry.delete(0, 'end')
                entry.insert(0, project_version)
                # Update config to remove override
                self.config_manager.config[config_key] = project_version
            
            # Set final state
            entry.configure(state=state)
            
        # Update config
        self.config_manager.config["use_version_override"] = enabled
        self.config_manager.save_config_silent()

        # Update version fields visibility
        self.update_version_fields_visibility()

        # If version override was just enabled, sync component versions with project version
        if enabled:
            self.force_project_version_update()

    def on_version_source_change(self, choice):
        """Handle version source dropdown changes"""
        self.config_manager.config["default_version_source"] = choice
        self.config_manager.save_config_silent()
        source_name = "Function Pack (FP/FPD)" if choice == "FP" else "Config-Service"
        print(f"Version source changed to: {source_name}")
    
    def toggle_default_versions(self):
        """Toggle the use default versions setting"""
        enabled = self.use_default_versions_var.get()

        # Mutual exclusion: disable version override when default versions is enabled
        if enabled and self.version_override_var.get():
            self.version_override_var.set(False)
            self.config_manager.config["use_version_override"] = False
            # Also disable the version entry fields
            self.toggle_version_override()
            print("Version override disabled: Default versions take precedence")

        # Update config
        self.config_manager.config["use_default_versions"] = enabled
        self.config_manager.save_config_silent()

        # Show informational message about what this does
        if enabled:
            source = self.config_manager.config.get("default_version_source", "FP")
            source_name = "Function Pack (FP/FPD)" if source == "FP" else "Config-Service"
            print(f"Default versions enabled: Installation script will fetch component versions from {source_name} API")
        else:
            print("Default versions disabled: Installation script will use hardcoded versions from GUI configuration")

        # Update version fields visibility
        self.update_version_fields_visibility()

    def on_project_version_change(self):
        """Handle changes to the main project version field"""
        try:
            # Get the new project version
            version_entry = self.config_manager.get_entry("version")
            if not version_entry:
                return

            new_version = version_entry.get().strip()
            if not new_version:
                return

            # Only update component versions if version override is enabled
            # and the component version fields exist
            if (hasattr(self, 'version_override_var') and
                self.version_override_var.get() and
                hasattr(self, 'pos_version_entry')):

                print(f"Project version changed to: {new_version}")
                print("Auto-updating component versions...")

                # List of component version entries to update
                component_entries = [
                    (self.pos_version_entry, "pos_version"),
                    (self.wdm_version_entry, "wdm_version"),
                    (self.flow_service_version_entry, "flow_service_version"),
                    (self.lpa_service_version_entry, "lpa_service_version"),
                    (self.storehub_service_version_entry, "storehub_service_version")
                ]

                # Update each component version field
                for entry, config_key in component_entries:
                    if entry:
                        # Get current value to avoid unnecessary updates
                        current_value = entry.get().strip()
                        if current_value != new_version:
                            # Clear and update the field
                            entry.delete(0, 'end')
                            entry.insert(0, new_version)
                            # Update the config
                            self.config_manager.config[config_key] = new_version

                # Save the config
                self.config_manager.save_config_silent()
                print("Component versions updated successfully!")
        except Exception as e:
            print(f"Error updating component versions: {e}")

    def force_project_version_update(self):
        """Force an update of component versions from project version"""
        self.on_project_version_change()

    def update_version_fields_visibility(self):
        """Update visibility of version input fields based on current settings"""
        # Version fields should only be visible when:
        # 1. Version override is enabled AND
        # 2. Default versions is disabled
        show_version_fields = (self.version_override_var.get() and not self.use_default_versions_var.get())

        if hasattr(self, 'version_fields'):
            for field in self.version_fields:
                if show_version_fields:
                    field.grid()  # Show the field
                else:
                    field.grid_remove()  # Hide the field but keep its grid position

    def test_default_versions_api(self):
        """Test the API to fetch default versions - shows modal to choose method"""
        try:
            # Force save current GUI values to config before testing
            print("\n" + "="*80)
            print("[TEST API] Starting API test...")
            print("="*80)
            print("[TEST API] Forcing config update from GUI fields...")
            self.config_manager.update_config_from_entries()
            self.config_manager.save_config_silent()

            # Get base URL from config
            base_url = self.config_manager.config.get("base_url", "")
            print(f"[TEST API] Retrieved base URL: {base_url}")
            if not base_url:
                print("[TEST API] ERROR: Base URL is empty!")
                messagebox.showerror("Error", "Please configure the Base URL first")
                return
            
            # Show modal dialog to choose API method
            self._show_api_method_dialog(base_url)

        except Exception as e:
            print(f"[TEST API] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
    
    def _show_api_method_dialog(self, base_url):
        """Show modal dialog to choose between API methods"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Choose API Method")
        dialog.geometry("500x250")
        dialog.transient(self.root)
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (250)
        y = (dialog.winfo_screenheight() // 2) - (125)
        dialog.geometry(f"500x250+{x}+{y}")
        
        # Title label
        title_label = ctk.CTkLabel(dialog, text="Select API Method", font=("Arial", 16, "bold"))
        title_label.pack(pady=20)
        
        # Description
        desc_label = ctk.CTkLabel(
            dialog, 
            text="Choose which API to use for fetching component versions:",
            wraplength=450
        )
        desc_label.pack(pady=10)
        
        # Button frame
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(pady=20, padx=20, fill="x")
        
        # Function Pack button
        fp_button = ctk.CTkButton(
            button_frame,
            text="Old Way (Function Pack)\n\nUses Employee Hub Function Pack API\nto fetch versions from FP/FPD scope",
            height=80,
            command=lambda: [dialog.destroy(), self._test_function_pack_api(base_url)]
        )
        fp_button.pack(side="left", expand=True, padx=5)
        
        # Config Service button
        cs_button = ctk.CTkButton(
            button_frame,
            text="New Way (Config-Service)\n\nUses Config-Service API to search\nversions by system name",
            height=80,
            command=lambda: [dialog.destroy(), self._test_config_service_api(base_url)]
        )
        cs_button.pack(side="left", expand=True, padx=5)
        
        # Update and grab
        dialog.update()
        try:
            dialog.grab_set()
        except Exception as e:
            print(f"[API METHOD] Warning: Could not grab window focus: {e}")
    
    def _test_function_pack_api(self, base_url):
        """Test the Employee Hub Function Pack API to fetch default versions"""
        try:
            # Show loading message
            print("[TEST API] Creating loading dialog...")
            loading_dialog = ctk.CTkToplevel(self.root)
            loading_dialog.title("Testing Function Pack API")
            loading_dialog.geometry("500x300")
            loading_dialog.transient(self.root)

            # Center the dialog
            loading_dialog.update_idletasks()
            x = (loading_dialog.winfo_screenwidth() // 2) - (500 // 2)
            y = (loading_dialog.winfo_screenheight() // 2) - (300 // 2)
            loading_dialog.geometry(f"500x300+{x}+{y}")

            loading_label = ctk.CTkLabel(loading_dialog, text="Testing Employee Hub Function Pack API...\nGenerating authentication token...\nPlease wait...", wraplength=450)
            loading_label.pack(expand=True, padx=20, pady=20)

            # Add a progress info label
            progress_label = ctk.CTkLabel(loading_dialog, text="Step 1 of 3: Authenticating...", text_color="gray")
            progress_label.pack(padx=20, pady=10)

            # Update the dialog and ensure it's visible before grabbing
            loading_dialog.update()
            loading_dialog.deiconify()  # Ensure window is visible

            # Try to grab focus with error handling for Linux compatibility
            try:
                loading_dialog.grab_set()
            except Exception as e:
                print(f"[TEST API] Warning: Could not grab window focus: {e}")
                # Continue without grab - dialog will still work

            # Try to generate token using credentials from config
            print("[TEST API] Step 1 of 3: Generating authentication token...")
            bearer_token = self._generate_api_token(base_url, loading_label, loading_dialog)

            if not bearer_token:
                print("[TEST API] ERROR: Failed to generate bearer token!")
                loading_dialog.destroy()
                messagebox.showerror("Authentication Failed",
                    "Could not generate authentication token.\n\n"
                    "💡 HINT: Please ensure all Security Configuration details are filled in first and that you can reach the Employee Hub itself.\n\n"
                    "1. Basic Auth Password (launchpad_oauth2)\n"
                    "2. Form Password (eh_launchpad_password)\n"
                    "3. Base URL is correct\n"
                    "4. Network connectivity\n\n"
                    "Go to the Security Configuration tab and complete all required fields.")
                return

            # Update loading message
            loading_label.configure(text="Testing Employee Hub Function Pack API...\nFetching component versions (FP scope)...\nPlease wait...")
            loading_dialog.update()

            # Prepare headers for API requests
            headers = {
                "authorization": f"Bearer {bearer_token}",
                "gk-tenant-id": "001",
                "Referer": f"https://{base_url}/employee-hub/app/index.html"
            }
            print(f"[TEST API] Headers prepared (token length: {len(bearer_token)})")
            print(f"[TEST API] Authorization: Bearer {bearer_token[:50]}...")  # Log truncated for security
            print(f"[TEST API] Referer: {headers['Referer']}")

            # Initialize versions tracking
            versions = {
                "POS": {"value": None, "source": None},
                "WDM": {"value": None, "source": None},
                "FLOW-SERVICE": {"value": None, "source": None},
                "LPA-SERVICE": {"value": None, "source": None},
                "STOREHUB-SERVICE": {"value": None, "source": None}
            }

            # Step 1: Try FP scope first (modified/customized versions)
            # Try multiple URL patterns as fallback
            fp_urls = [
                f"https://{base_url}/api/employee-hub-service/services/rest/v1/properties?scope=FP&referenceId=platform",
                f"https://{base_url}/employee-hub-service/services/rest/v1/properties?scope=FP&referenceId=platform"
            ]
            
            print(f"[TEST API] Step 2 of 3: Fetching FP scope...")
            fp_response = None
            fp_success = False
            
            for i, fp_api_url in enumerate(fp_urls):
                print(f"[TEST API] Trying FP URL pattern {i+1}/{len(fp_urls)}: {fp_api_url}")
                
                try:
                    print(f"[TEST API] Making FP scope request...")
                    print(f"[TEST API] Request method: GET")
                    if i == 0:  # Only print headers on first attempt to avoid spam
                        print(f"[TEST API] Request headers:")
                        for key, value in headers.items():
                            if key == "authorization":
                                print(f"[TEST API]   {key}: Bearer {value.replace('Bearer ', '')[:50]}...")
                            else:
                                print(f"[TEST API]   {key}: {value}")
                    
                    fp_response = requests.get(fp_api_url, headers=headers, timeout=30, verify=False)
                    print(f"[TEST API] FP response status code: {fp_response.status_code}")
                    
                    if fp_response.status_code == 200:
                        print(f"[TEST API] ✅ FP URL pattern {i+1} worked!")
                        print(f"[TEST API] FP response headers: {dict(fp_response.headers)}")
                        print(f"[TEST API] FP response length: {len(fp_response.text)} bytes")
                        fp_success = True
                        break
                    else:
                        print(f"[TEST API] ❌ FP URL pattern {i+1} returned {fp_response.status_code}")
                        if i == len(fp_urls) - 1:  # Last attempt, show response
                            print(f"[TEST API] Response text: {fp_response.text[:500]}")
                        continue
                        
                except Exception as e:
                    print(f"[TEST API] ❌ FP URL pattern {i+1} failed: {e}")
                    if i == len(fp_urls) - 1:  # Last attempt failed
                        print(f"[TEST API] All FP URL patterns failed")
                    continue
            
            if fp_success:
                try:
                    print(f"[TEST API] Full response body:")
                    print(f"[TEST API] {fp_response.text}")
                    print(f"[TEST API] " + "-"*80)
                    
                    fp_data = fp_response.json()
                    print(f"[TEST API] FP response parsed successfully (items: {len(fp_data) if isinstance(fp_data, list) else 'N/A'})")
                    print(f"[TEST API] FP response type: {type(fp_data)}")
                    print(f"[TEST API] Raw FP data (first 500 chars): {str(fp_data)[:500]}")

                    # Parse FP scope results
                    if isinstance(fp_data, list):
                        for idx, property_item in enumerate(fp_data):
                            prop_id = property_item.get("propertyId", "")
                            value = property_item.get("value", "")
                            print(f"[TEST API]   Item {idx}: propertyId='{prop_id}', value='{value}'")

                            # POS: try Update_Version first, fallback to Version
                            if prop_id in ["POSClient_Update_Version", "POSClient_Version"] and value:
                                if versions["POS"]["value"] is None or prop_id == "POSClient_Update_Version":
                                    versions["POS"] = {"value": value, "source": "FP (Modified)"}
                                    print(f"[TEST API]     -> Matched POS ({prop_id}): {value}")
                            # WDM: try Version first, fallback to Update_Version
                            elif prop_id in ["WDM_Version", "WDM_Update_Version"] and value:
                                if versions["WDM"]["value"] is None or prop_id == "WDM_Version":
                                    versions["WDM"] = {"value": value, "source": "FP (Modified)"}
                                    print(f"[TEST API]     -> Matched WDM ({prop_id}): {value}")
                            # FlowService: try Version first, fallback to Update_Version
                            elif prop_id in ["FlowService_Version", "FlowService_Update_Version"] and value:
                                if versions["FLOW-SERVICE"]["value"] is None or prop_id == "FlowService_Version":
                                    versions["FLOW-SERVICE"] = {"value": value, "source": "FP (Modified)"}
                                    print(f"[TEST API]     -> Matched FlowService ({prop_id}): {value}")
                            # LPA: try Version first, fallback to Update_Version
                            elif prop_id in ["LPA_Version", "LPA_Update_Version"] and value:
                                if versions["LPA-SERVICE"]["value"] is None or prop_id == "LPA_Version":
                                    versions["LPA-SERVICE"] = {"value": value, "source": "FP (Modified)"}
                                    print(f"[TEST API]     -> Matched LPA ({prop_id}): {value}")
                            # StoreHub: try Update_Version first, fallback to Version
                            elif prop_id in ["SH_Update_Version", "StoreHub_Version"] and value:
                                if versions["STOREHUB-SERVICE"]["value"] is None or prop_id == "SH_Update_Version":
                                    versions["STOREHUB-SERVICE"] = {"value": value, "source": "FP (Modified)"}
                                    print(f"[TEST API]     -> Matched StoreHub ({prop_id}): {value}")
                    else:
                        print(f"[TEST API] ERROR: FP response is not a list, it's a {type(fp_data)}")
                except Exception as json_err:
                    print(f"[TEST API] ERROR parsing FP JSON: {json_err}")
                    print(f"[TEST API] Response text: {fp_response.text[:500]}")

            # Step 2: For components not found in FP, try FPD scope (default versions)
            missing_components = [comp for comp, data in versions.items() if data["value"] is None]

            if missing_components:
                loading_label.configure(text="Testing Employee Hub Function Pack API...\nFetching missing components (FPD scope)...\nPlease wait...")
                loading_dialog.update()

                # Try multiple URL patterns for FPD as well
                fpd_urls = [
                    f"https://{base_url}/api/employee-hub-service/services/rest/v1/properties?scope=FPD&referenceId=platform",
                    f"https://{base_url}/employee-hub-service/services/rest/v1/properties?scope=FPD&referenceId=platform"
                ]
                
                fpd_response = None
                fpd_success = False
                
                for i, fpd_api_url in enumerate(fpd_urls):
                    print(f"[TEST API] Trying FPD URL pattern {i+1}/{len(fpd_urls)}: {fpd_api_url}")
                    
                    try:
                        fpd_response = requests.get(fpd_api_url, headers=headers, timeout=30, verify=False)
                        print(f"[TEST API] FPD response status code: {fpd_response.status_code}")
                        
                        if fpd_response.status_code == 200:
                            print(f"[TEST API] ✅ FPD URL pattern {i+1} worked!")
                            fpd_success = True
                            break
                        else:
                            print(f"[TEST API] ❌ FPD URL pattern {i+1} returned {fpd_response.status_code}")
                            continue
                    except Exception as e:
                        print(f"[TEST API] ❌ FPD URL pattern {i+1} failed: {e}")
                        continue

                if fpd_success:
                    try:
                        fpd_data = fpd_response.json()

                        # Parse FPD scope results for missing components only
                        for property_item in fpd_data:
                            prop_id = property_item.get("propertyId", "")
                            value = property_item.get("value", "")

                            # POS: try Update_Version first, fallback to Version
                            if prop_id in ["POSClient_Update_Version", "POSClient_Version"] and value and versions["POS"]["value"] is None:
                                versions["POS"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched POS ({prop_id}): {value}")
                            # WDM: try Version first, fallback to Update_Version
                            elif prop_id in ["WDM_Version", "WDM_Update_Version"] and value and versions["WDM"]["value"] is None:
                                versions["WDM"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched WDM ({prop_id}): {value}")
                            # FlowService: try Version first, fallback to Update_Version
                            elif prop_id in ["FlowService_Version", "FlowService_Update_Version"] and value and versions["FLOW-SERVICE"]["value"] is None:
                                versions["FLOW-SERVICE"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched FlowService ({prop_id}): {value}")
                            # LPA: try Version first, fallback to Update_Version
                            elif prop_id in ["LPA_Version", "LPA_Update_Version"] and value and versions["LPA-SERVICE"]["value"] is None:
                                versions["LPA-SERVICE"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched LPA ({prop_id}): {value}")
                            # StoreHub: try Update_Version first, fallback to Version
                            elif prop_id in ["SH_Update_Version", "StoreHub_Version"] and value and versions["STOREHUB-SERVICE"]["value"] is None:
                                versions["STOREHUB-SERVICE"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched StoreHub ({prop_id}): {value}")
                    except Exception as e:
                        print(f"Warning: FPD scope request failed: {e}")

            loading_dialog.destroy()

            # Show results with status and source for each component
            print(f"[TEST API] Test complete. Processing results...")
            result_text = "✅ API Test Successful!\n\nComponent Version Status:\n\n"

            found_count = 0
            for component, data in versions.items():
                if data["value"]:
                    result_text += f"✅ {component}: {data['value']} ({data['source']})\n"
                    found_count += 1
                    print(f"[TEST API] ✅ {component}: {data['value']} ({data['source']})")
                else:
                    result_text += f"❌ {component}: Not Found\n"
                    print(f"[TEST API] ❌ {component}: Not Found")

            result_text += f"\n📊 Summary: {found_count}/5 components found"
            result_text += f"\n🔍 Search Strategy: FP scope first, FPD scope for missing components"

            if found_count == 0:
                result_text += "\n\n⚠️ No component versions found in either FP or FPD scope"

            print(f"[TEST API] " + "="*80)
            print(f"[TEST API] SUMMARY: {found_count}/5 components found")
            print(f"[TEST API] " + "="*80)
            messagebox.showinfo("API Test Results", result_text)

        except requests.exceptions.RequestException as e:
            if 'loading_dialog' in locals():
                loading_dialog.destroy()
            messagebox.showerror("API Test Failed",
                f"Network error: {str(e)}\n\n"
                f"💡 HINT: Please check your network connection and ensure all Security Configuration details are filled in first.")
        except Exception as e:
            if 'loading_dialog' in locals():
                loading_dialog.destroy()
            messagebox.showerror("API Test Failed",
                f"Error: {str(e)}\n\n"
                f"💡 HINT: Please ensure all Security Configuration details are filled in first.")

    def _generate_api_token(self, base_url, loading_label, loading_dialog):
        """Generate API token using credentials from config"""
        try:
            # Update loading message
            loading_label.configure(text="Generating authentication token...\nUsing credentials from configuration...")
            loading_dialog.update()

            # Get the correct credentials from config
            # Note: These come from the Security Configuration section
            basic_auth_password = self.config_manager.config.get("launchpad_oauth2", "")  # Basic Auth password (for launchpad:password)
            form_username = self.config_manager.config.get("eh_launchpad_username", "")  # Form username (e.g., gk01ag)
            form_password = self.config_manager.config.get("eh_launchpad_password", "")  # Form password (e.g., gk12345)
            
            print(f"[TOKEN GEN] basic_auth_password present: {bool(basic_auth_password)} (length: {len(basic_auth_password) if basic_auth_password else 0})")
            print(f"[TOKEN GEN] form_username present: {bool(form_username)} (length: {len(form_username) if form_username else 0})")
            print(f"[TOKEN GEN] form_password present: {bool(form_password)} (length: {len(form_password) if form_password else 0})")
            print(f"[TOKEN GEN] Config keys: {list(self.config_manager.config.keys())}")

            if not basic_auth_password or not form_username or not form_password:
                print(f"[TOKEN GEN] ERROR: Missing credentials!")
                print(f"[TOKEN GEN]   launchpad_oauth2: {bool(basic_auth_password)}")
                print(f"[TOKEN GEN]   eh_launchpad_username: {bool(form_username)}")
                print(f"[TOKEN GEN]   eh_launchpad_password: {bool(form_password)}")
                return None

            # Handle both base64 encoded and plain text passwords
            import base64
            try:
                # Try to decode as base64 first
                basic_auth_password_decoded = base64.b64decode(basic_auth_password).decode('utf-8')
                form_password_decoded = base64.b64decode(form_password).decode('utf-8')
                basic_auth_password = basic_auth_password_decoded
                form_password = form_password_decoded
            except Exception:
                # Use the passwords as-is (they're already plain text)
                pass

            # Create Basic Auth header
            username = "launchpad"
            auth_string = f"{username}:{basic_auth_password}"
            auth_b64 = base64.b64encode(auth_string.encode('ascii')).decode('ascii')

            # Prepare form data
            import urllib.parse
            form_data_dict = {
                'username': form_username,  # Use the username from config (e.g., gk01ag)
                'password': form_password,
                'grant_type': 'password'
            }

            # URL encode form data
            encoded_pairs = []
            for key, value in form_data_dict.items():
                encoded_key = urllib.parse.quote_plus(str(key))
                encoded_value = urllib.parse.quote_plus(str(value))
                encoded_pairs.append(f"{encoded_key}={encoded_value}")

            form_data = '&'.join(encoded_pairs)

            # Make OAuth token request
            token_url = f"https://{base_url}/auth-service/tenants/001/oauth/token"
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            print(f"[TOKEN GEN] Token URL: {token_url}")
            print(f"[TOKEN GEN] Auth header: Basic {auth_b64[:50]}...")
            print(f"[TOKEN GEN] Form data keys: {list(form_data_dict.keys())}")
            print(f"[TOKEN GEN] Form data (encoded): {form_data[:100]}...")

            # Update loading message
            loading_label.configure(text="Requesting OAuth token...\nPlease wait...")
            loading_dialog.update()

            # Disable SSL warnings for this request
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            print(f"[TOKEN GEN] Sending POST request...")
            response = requests.post(token_url, headers=headers, data=form_data, timeout=30, verify=False)
            
            print(f"[TOKEN GEN] Token response status: {response.status_code}")
            print(f"[TOKEN GEN] Token response text: {response.text[:500]}")
            print(f"[TOKEN GEN] Token response headers: {dict(response.headers)}")

            if response.status_code == 200:
                try:
                    token_data = response.json()
                    access_token = token_data.get('access_token')
                    if access_token:
                        print(f"[TOKEN GEN] ✅ Token generated successfully (length: {len(access_token)})")
                        return access_token
                    else:
                        print(f"[TOKEN GEN] ERROR: No access_token in response")
                except Exception as e:
                    print(f"[TOKEN GEN] ERROR parsing token response: {e}")
                    pass
            else:
                print(f"[TOKEN GEN] ERROR: Non-200 status code: {response.status_code}")

            print(f"[TOKEN GEN] Returning None - token generation failed")
            return None

        except Exception as e:
            print(f"[TOKEN GEN] EXCEPTION in _generate_api_token: {e}")
            import traceback
            print(f"[TOKEN GEN] Traceback: {traceback.format_exc()}")
            return None
    
    def _test_config_service_api(self, base_url):
        """Test the Config-Service API to fetch versions by system name"""
        try:
            # Show loading message
            print("[CONFIG API] Creating loading dialog...")
            loading_dialog = ctk.CTkToplevel(self.root)
            loading_dialog.title("Testing Config-Service API")
            loading_dialog.geometry("500x300")
            loading_dialog.transient(self.root)

            # Center the dialog
            loading_dialog.update_idletasks()
            x = (loading_dialog.winfo_screenwidth() // 2) - (250)
            y = (loading_dialog.winfo_screenheight() // 2) - (150)
            loading_dialog.geometry(f"500x300+{x}+{y}")

            loading_label = ctk.CTkLabel(loading_dialog, text="Testing Config-Service API...\nGenerating authentication token...\nPlease wait...", wraplength=450)
            loading_label.pack(expand=True, padx=20, pady=20)

            # Update the dialog and ensure it's visible
            loading_dialog.update()
            loading_dialog.deiconify()

            # Try to grab focus
            try:
                loading_dialog.grab_set()
            except Exception as e:
                print(f"[CONFIG API] Warning: Could not grab window focus: {e}")

            # Generate token
            print("[CONFIG API] Step 1: Generating authentication token...")
            bearer_token = self._generate_api_token(base_url, loading_label, loading_dialog)

            if not bearer_token:
                print("[CONFIG API] ERROR: Failed to generate bearer token!")
                loading_dialog.destroy()
                messagebox.showerror("Authentication Failed",
                    "Could not generate authentication token.\n\n"
                    "💡 HINT: Please ensure all Security Configuration details are filled in first.")
                return

            # Update loading message
            loading_label.configure(text="Testing Config-Service API...\nFetching versions for all components...\nPlease wait...")
            loading_dialog.update()

            # Prepare headers
            headers = {
                "authorization": f"Bearer {bearer_token}",
                "content-type": "application/json"
            }
            print(f"[CONFIG API] Headers prepared (token length: {len(bearer_token)})")

            # Get system types from config
            system_types = {
                "POS": self.config_manager.config.get("pos_system_type", "GKR-OPOS-CLOUD"),
                "WDM": self.config_manager.config.get("wdm_system_type", "CSE-wdm"),
                "FLOW-SERVICE": self.config_manager.config.get("flow_service_system_type", "GKR-FLOWSERVICE-CLOUD"),
                "LPA-SERVICE": self.config_manager.config.get("lpa_service_system_type", "CSE-lps-lpa"),
                "STOREHUB-SERVICE": self.config_manager.config.get("storehub_service_system_type", "CSE-sh-cloud")
            }

            print(f"[CONFIG API] System types: {system_types}")

            # Initialize versions tracking
            versions = {}
            
            # Disable SSL warnings
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # API URL
            api_url = f"https://{base_url}/api/config/services/rest/infrastructure/v1/versions/search"
            print(f"[CONFIG API] API URL: {api_url}")

            # Fetch versions for each component
            for component, system_name in system_types.items():
                print(f"[CONFIG API] Fetching versions for {component} (systemName: {system_name})...")
                
                payload = {"systemName": system_name}
                
                try:
                    response = requests.post(api_url, headers=headers, json=payload, timeout=30, verify=False)
                    print(f"[CONFIG API] {component} response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        version_list = data.get("versionNameList", [])
                        
                        if version_list:
                            # Take the first version (latest)
                            latest_version = version_list[0]
                            versions[component] = {"value": latest_version, "source": "Config-Service", "all_versions": version_list}
                            print(f"[CONFIG API] ✅ {component}: {latest_version} (available: {len(version_list)} versions)")
                        else:
                            versions[component] = {"value": None, "source": None, "all_versions": []}
                            print(f"[CONFIG API] ❌ {component}: No versions found")
                    else:
                        print(f"[CONFIG API] ❌ {component} returned status {response.status_code}: {response.text[:200]}")
                        versions[component] = {"value": None, "source": None, "all_versions": []}
                        
                except Exception as e:
                    print(f"[CONFIG API] ❌ {component} request failed: {e}")
                    versions[component] = {"value": None, "source": None, "all_versions": []}

            loading_dialog.destroy()

            # Show results
            print(f"[CONFIG API] Test complete. Processing results...")
            result_text = "✅ Config-Service API Test Successful!\n\nComponent Version Status:\n\n"

            found_count = 0
            for component, data in versions.items():
                if data["value"]:
                    all_versions_str = ", ".join(data.get("all_versions", [])[:3])  # Show first 3 versions
                    if len(data.get("all_versions", [])) > 3:
                        all_versions_str += "..."
                    result_text += f"✅ {component}: {data['value']}\n   Available: {all_versions_str}\n\n"
                    found_count += 1
                    print(f"[CONFIG API] ✅ {component}: {data['value']}")
                else:
                    result_text += f"❌ {component}: Not Found\n\n"
                    print(f"[CONFIG API] ❌ {component}: Not Found")

            result_text += f"📊 Summary: {found_count}/5 components found"
            result_text += f"\n🔍 API: Config-Service (versions/search)"

            if found_count == 0:
                result_text += "\n\n⚠️ No component versions found"

            print(f"[CONFIG API] " + "="*80)
            print(f"[CONFIG API] SUMMARY: {found_count}/5 components found")
            print(f"[CONFIG API] " + "="*80)
            messagebox.showinfo("Config-Service API Test Results", result_text)

        except requests.exceptions.RequestException as e:
            if 'loading_dialog' in locals():
                loading_dialog.destroy()
            messagebox.showerror("API Test Failed",
                f"Network error: {str(e)}\n\n"
                f"💡 HINT: Please check your network connection.")
        except Exception as e:
            if 'loading_dialog' in locals():
                loading_dialog.destroy()
            messagebox.showerror("API Test Failed",
                f"Error: {str(e)}\n\n"
                f"💡 HINT: Please ensure all configuration details are correct.")

    def create_output_selection(self):
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", padx=10, pady=(0, 20))
        
        # Label with tooltip
        label = ctk.CTkLabel(
            frame,
            text="Output Directory:",
            width=150
        )
        label.pack(side="left", padx=10)
        
        # Create tooltip for the label
        self.create_tooltip(label, "Directory where generated installation files will be saved (automatically set based on Project Name and Base URL)")
        
        # Allow the output directory to be edited
        self.output_dir_entry = ctk.CTkEntry(frame, width=300)  # Changed from 200 to 300
        self.output_dir_entry.pack(side="left", padx=10, expand=False)
        
        # Get the initial value from config or set a default
        initial_output_dir = self.config_manager.config.get("output_dir", "")
        self.output_dir_entry.insert(0, initial_output_dir)
        
        # Create tooltip for the entry
        self.create_tooltip(self.output_dir_entry, "Directory where generated installation files will be saved (automatically set based on Project Name and Base URL)")
        
        # Register with config manager
        self.config_manager.register_entry("output_dir", self.output_dir_entry)
        
        # Add a function to update output directory when project name or base URL changes
        def update_output_dir_on_name_change(event=None):
            # Get the base URL
            base_url = self.config_manager.get_entry("base_url").get() if self.config_manager.get_entry("base_url") else ""
            
            # First try to extract project name from URL if needed
            extracted_project_name = ""
            if "." in base_url:
                parts = base_url.split(".")
                if len(parts) > 1:
                    extracted_project_name = parts[1].upper()
            
            # Get current project name (from entry or extracted)
            project_name = self.config_manager.get_entry("project_name").get() if self.config_manager.get_entry("project_name") else extracted_project_name
            
            if project_name and base_url:
                # Create the output directory structure
                output_dir = os.path.join(project_name, base_url)
                self.output_dir_entry.delete(0, 'end')
                self.output_dir_entry.insert(0, output_dir)
                self.config_manager.config["output_dir"] = output_dir
        
        # Bind the project name and base URL fields to update output directory
        if self.config_manager.get_entry("project_name"):
            self.config_manager.get_entry("project_name").bind("<KeyRelease>", update_output_dir_on_name_change)
        
        if self.config_manager.get_entry("base_url"):
            self.config_manager.get_entry("base_url").bind("<KeyRelease>", update_output_dir_on_name_change)
    
    def create_status_label(self):
        """Create a status label for auto-save feedback"""
        status_frame = ctk.CTkFrame(self.main_frame)
        status_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        # Create and configure the status label
        self.save_status_label = ctk.CTkLabel(
            status_frame,
            text="",
            font=("Helvetica", 12),
            anchor="e"
        )
        self.save_status_label.pack(side="right", padx=10)
        
        # Register the status label with the config manager
        self.config_manager.set_save_status_label(self.save_status_label)
    
    def create_buttons(self):
        # Create frame for buttons
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # Add button to open launcher settings editor
        edit_launchers_button = ctk.CTkButton(
            button_frame,
            text="Edit Launcher Settings",
            command=self.open_launcher_editor
        )
        edit_launchers_button.pack(side="left", padx=10)
        
        # Create button to open offline package creator
        offline_button = ctk.CTkButton(
            button_frame,
            text="Create Offline Package",
            command=self.open_offline_package_creator
        )
        offline_button.pack(side="left", padx=10)
        
        # Create generate button
        generate_button = ctk.CTkButton(
            button_frame,
            text="Generate Installation Files",
            command=self.generate_installation_files
        )
        generate_button.pack(side="right", padx=10)
    
    def show_author_info(self):
        """Display author information in a dialog (delegates to AboutDialog)"""
        about_dialog = AboutDialog(self.root)
        about_dialog.show()
    
        """Update the KeePass button state based on whether credentials are stored"""
        # Skip if the keepass_button doesn't exist
        if not hasattr(self, 'keepass_button') or not self.keepass_button:
            return
            
        if self.keepass_client and self.keepass_username and self.keepass_password:
            # We have credentials, show the disconnect button
            self.keepass_button.configure(
                text="Disconnect from KeePass",
                command=self.clear_keepass_credentials
            )
        else:
            # No credentials, show the connect button
            self.keepass_button.configure(
                text="Connect to KeePass",
                command=self.get_basic_auth_password_from_keepass
            )
    
    def on_window_close(self):
        """Handle window close event"""
        try:
            # Update config from entries
            self.config_manager.update_config_from_entries()
            
            # Clean up entries
            for entry in list(self.config_manager.entries):
                if hasattr(entry, 'widget') and entry.widget.winfo_toplevel() == self.root:
                    self.config_manager.unregister_entry(entry)
            
            # Force close any active download dialogs
            for widget in self.root.winfo_children():
                if isinstance(widget, ctk.CTkToplevel):
                    try:
                        widget.destroy()
                    except Exception:
                        pass
            
            # Cancel any pending after() callbacks to prevent errors after window destruction
            try:
                for after_id in self.root.tk.call('after', 'info'):
                    self.root.after_cancel(after_id)
            except Exception:
                pass
            
            # Release window grab and destroy
            try:
                self.root.grab_release()
            except Exception:
                pass
            
            # Withdraw the window first to prevent visual glitches
            try:
                self.root.withdraw()
            except Exception:
                pass
                
            self.root.destroy()
            
            # Restore parent window and rebind events
            if hasattr(self, 'parent_app') and self.parent_app:
                # Restore main window focus
                self.parent_app.root.focus_force()
                
                # Rebind base URL events
                base_url_entry = self.parent_app.config_manager.get_entry("base_url")
                if base_url_entry:
                    base_url_entry.bind("<FocusOut>", self.parent_app.on_base_url_changed)
                    
                # Ensure refresh button is properly set up
                if hasattr(self.parent_app, 'refresh_button'):
                    self.parent_app.refresh_button.configure(command=self.parent_app.regenerate_configuration)
                    
        except Exception as e:
            print(f"Error during window close: {e}")
    
    def open_offline_package_creator(self):
        """Open the Offline Package Creator window"""
        # If window exists, bring it to front
        if hasattr(self, 'offline_creator') and self.offline_creator:
            try:
                self.offline_creator.window.focus_force()
                return
            except:
                self.offline_creator = None

        # Create new offline package creator
        self.offline_creator = OfflinePackageCreator(
            self.root,
            self.config_manager,
            self.project_generator,
            parent_app=self
        )

    def open_detection_settings(self):
        """Open the Detection Settings dialog (delegates to DetectionSettingsDialog)"""
        dialog = DetectionSettingsDialog(
            self.root,
            self.config_manager,
            self.detection_manager,
            self.hostname_detection_var,
            self.detection_var,
            parent_app=self
        )
        dialog.show()

    def show_error(self, title, message):
        """Show error dialog"""
        messagebox.showerror(title, message)

    def show_info(self, title, message):
        """Show info dialog"""
        messagebox.showinfo(title, message)

    def get_basic_auth_password_from_keepass(self, target_entry=None, password_type="basic_auth"):
        """Get password from KeePass"""
        from keepass_dialog import KeePassDialog
        
        # If no target entry is specified, use the appropriate password entry based on type
        if target_entry is None:
            if password_type == "basic_auth":
                target_entry = self.basic_auth_password_entry
            elif password_type == "webdav_admin":
                target_entry = self.webdav_admin_password_entry
        
        # Create callback to get base URL from config
        def get_base_url():
            return self.config_manager.config.get("base_url", "")
        
        # Create and open the KeePass dialog
        keepass_dialog = KeePassDialog(
            parent=self.root,
            target_entry=target_entry,
            base_url_callback=get_base_url
        )
        keepass_dialog.open()
            
    
    def find_basic_auth_password_entry(self, folder_structure):
        """Find Basic Auth password entry in KeePass folder structure"""
        print("\nSearching for Basic Auth password entry...")
        env_name = None

        # Try to extract environment name from folder structure
        if isinstance(folder_structure, dict):
            folder_name = folder_structure.get('Name', '')
            if folder_name:
                env_name = folder_name
                print(f"Current environment: {env_name}")

        # Create a list to store all found credentials for debugging
        all_credentials = []
        found_entries = []
        target_entry = None

        def search_recursively(structure, path=""):
            """Recursively search for credentials in the folder structure"""
            nonlocal target_entry

            if not isinstance(structure, dict):
                return None

            # Check credentials in current folder
            credentials = structure.get('Credentials', [])
            folder_name = structure.get('Name', '')
            current_path = f"{path}/{folder_name}" if path else folder_name

            print(f"Checking folder: {current_path} - Found {len(credentials)} credentials")

            # Look for credentials in this folder
            for cred in credentials:
                cred_name = cred.get('Name', '')
                cred_id = cred.get('Id', '')
                all_credentials.append({
                    'path': current_path,
                    'name': cred_name,
                    'id': cred_id
                })

                # Dynamically build the target credential names based on environment
                if env_name:
                    # Support both naming formats: dashes and underscores
                    target_cred_name_dash = f"{env_name}-LAUNCHPAD-OAUTH-BA-PASSWORD"
                    target_cred_name_underscore = f"{env_name}_LAUNCHPAD_OAUTH_BA_PASSWORD"

                    # First priority: exact match for dash format in APP subfolder
                    if cred_name == target_cred_name_dash and "APP" in current_path:
                        print(f"FOUND TARGET ENTRY (dash format): {target_cred_name_dash} in {current_path}")
                        target_entry = cred
                        return cred

                    # First priority: exact match for underscore format in APP subfolder
                    if cred_name == target_cred_name_underscore and "APP" in current_path:
                        print(f"FOUND TARGET ENTRY (underscore format): {target_cred_name_underscore} in {current_path}")
                        target_entry = cred
                        return cred

                    # Second priority: exact match for dash format anywhere
                    if cred_name == target_cred_name_dash:
                        print(f"FOUND EXACT MATCH (dash format): {target_cred_name_dash} in {current_path}")
                        found_entries.append({
                            'priority': 1,
                            'entry': cred,
                            'path': current_path,
                            'reason': f'Exact match for {target_cred_name_dash} (dash format)'
                        })

                    # Second priority: exact match for underscore format anywhere
                    if cred_name == target_cred_name_underscore:
                        print(f"FOUND EXACT MATCH (underscore format): {target_cred_name_underscore} in {current_path}")
                        found_entries.append({
                            'priority': 1,
                            'entry': cred,
                            'path': current_path,
                            'reason': f'Exact match for {target_cred_name_underscore} (underscore format)'
                        })

            # Third priority: entries with LAUNCHPAD-OAUTH-BA-PASSWORD (dash format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'LAUNCHPAD-OAUTH-BA-PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains LAUNCHPAD-OAUTH-BA-PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 2,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains LAUNCHPAD-OAUTH-BA-PASSWORD: {cred_name} (dash format)'
                    })

            # Third priority: entries with LAUNCHPAD_OAUTH_BA_PASSWORD (underscore format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'LAUNCHPAD_OAUTH_BA_PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains LAUNCHPAD_OAUTH_BA_PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 2,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains LAUNCHPAD_OAUTH_BA_PASSWORD: {cred_name} (underscore format)'
                    })

            # Fourth priority: entries with BA-PASSWORD (dash format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'BA-PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains BA-PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 3,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains BA-PASSWORD: {cred_name} (dash format)'
                    })

            # Fourth priority: entries with BA_PASSWORD (underscore format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'BA_PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains BA_PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 3,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains BA_PASSWORD: {cred_name} (underscore format)'
                    })

            # Fifth priority: entries with rare format LAUNCHPAD_OAUTH
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if cred_name == 'LAUNCHPAD_OAUTH':
                    print(f"FOUND MATCH: Rare format LAUNCHPAD_OAUTH in {current_path}")
                    found_entries.append({
                        'priority': 4,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Rare format: LAUNCHPAD_OAUTH'
                    })
            
            # Check children folders
            children = structure.get('Children', [])
            for child in children:
                result = search_recursively(child, current_path)
                if result:
                    return result
                    
            return None
        
        # Start recursive search
        result = search_recursively(folder_structure)
        
        # If we found the target entry, return it
        if target_entry:
            return target_entry
        
        # If no exact match found but we have other matches, use the highest priority one
        if not result and found_entries:
            # Sort by priority (lowest number = highest priority)
            found_entries.sort(key=lambda x: x['priority'])
            best_match = found_entries[0]
            print(f"\nNo exact match for {env_name}-LAUNCHPAD-OAUTH-BA-PASSWORD or {env_name}_LAUNCHPAD_OAUTH_BA_PASSWORD found in APP subfolder.")
            print(f"Using best match: {best_match['reason']} in {best_match['path']}")
            return best_match['entry']
        
        # If no result found, print all credentials for debugging
        if not result and not found_entries:
            print("\nAll credentials found during search:")
            for cred in all_credentials:
                print(f"  - {cred['path']}: {cred['name']} (ID: {cred['id']})")
            
        return result
    
    def find_webdav_admin_password_entry(self, folder_structure):
        """Find Webdav Admin password entry in KeePass folder structure"""
        print("\nSearching for Webdav Admin password entry...")
        env_name = None

        # Try to extract environment name from folder structure
        if isinstance(folder_structure, dict):
            folder_name = folder_structure.get('Name', '')
            if folder_name:
                env_name = folder_name
                print(f"Current environment: {env_name}")

        # Create a list to store all found credentials for debugging
        all_credentials = []
        found_entries = []
        target_entry = None

        def search_recursively(structure, path=""):
            """Recursively search for credentials in the folder structure"""
            nonlocal target_entry

            if not isinstance(structure, dict):
                return None

            # Check credentials in current folder
            credentials = structure.get('Credentials', [])
            folder_name = structure.get('Name', '')
            current_path = f"{path}/{folder_name}" if path else folder_name

            print(f"Checking folder: {current_path} - Found {len(credentials)} credentials")

            # Look for credentials in this folder
            for cred in credentials:
                cred_name = cred.get('Name', '')
                cred_id = cred.get('Id', '')
                all_credentials.append({
                    'path': current_path,
                    'name': cred_name,
                    'id': cred_id
                })

                # Dynamically build the target credential names based on environment
                if env_name:
                    # Support both naming formats: dashes and underscores
                    target_cred_name_dash = f"{env_name}-DSG-WEBDAV-ADMIN-PASSWORD"
                    target_cred_name_underscore = f"{env_name}_DSG_WEBDAV_ADMIN_PASSWORD"

                    # First priority: exact match for dash format in APP subfolder
                    if cred_name == target_cred_name_dash and "APP" in current_path:
                        print(f"FOUND TARGET ENTRY (dash format): {target_cred_name_dash} in {current_path}")
                        target_entry = cred
                        return cred

                    # First priority: exact match for underscore format in APP subfolder
                    if cred_name == target_cred_name_underscore and "APP" in current_path:
                        print(f"FOUND TARGET ENTRY (underscore format): {target_cred_name_underscore} in {current_path}")
                        target_entry = cred
                        return cred

                    # Second priority: exact match for dash format anywhere
                    if cred_name == target_cred_name_dash:
                        print(f"FOUND EXACT MATCH (dash format): {target_cred_name_dash} in {current_path}")
                        found_entries.append({
                            'priority': 1,
                            'entry': cred,
                            'path': current_path,
                            'reason': f'Exact match for {target_cred_name_dash} (dash format)'
                        })

                    # Second priority: exact match for underscore format anywhere
                    if cred_name == target_cred_name_underscore:
                        print(f"FOUND EXACT MATCH (underscore format): {target_cred_name_underscore} in {current_path}")
                        found_entries.append({
                            'priority': 1,
                            'entry': cred,
                            'path': current_path,
                            'reason': f'Exact match for {target_cred_name_underscore} (underscore format)'
                        })

            # Third priority: entries with DSG-WEBDAV-ADMIN-PASSWORD (dash format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'DSG-WEBDAV-ADMIN-PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains DSG-WEBDAV-ADMIN-PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 2,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains DSG-WEBDAV-ADMIN-PASSWORD: {cred_name} (dash format)'
                    })

            # Third priority: entries with DSG_WEBDAV_ADMIN_PASSWORD (underscore format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'DSG_WEBDAV_ADMIN_PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains DSG_WEBDAV_ADMIN_PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 2,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains DSG_WEBDAV_ADMIN_PASSWORD: {cred_name} (underscore format)'
                    })

            # Fourth priority: entries with WEBDAV-ADMIN-PASSWORD (dash format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'WEBDAV-ADMIN-PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains WEBDAV-ADMIN-PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 3,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains WEBDAV-ADMIN-PASSWORD: {cred_name} (dash format)'
                    })

            # Fourth priority: entries with WEBDAV_ADMIN_PASSWORD (underscore format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'WEBDAV_ADMIN_PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains WEBDAV_ADMIN_PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 3,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains WEBDAV_ADMIN_PASSWORD: {cred_name} (underscore format)'
                    })
            
            # Check children folders
            children = structure.get('Children', [])
            for child in children:
                result = search_recursively(child, current_path)
                if result:
                    return result
                    
            return None
        
        # Start recursive search
        result = search_recursively(folder_structure)
        
        # If we found the target entry, return it
        if target_entry:
            return target_entry
        
        # If no exact match found but we have other matches, use the highest priority one
        if not result and found_entries:
            # Sort by priority (lowest number = highest priority)
            found_entries.sort(key=lambda x: x['priority'])
            best_match = found_entries[0]
            print(f"\nNo exact match for {env_name}-DSG-WEBDAV-ADMIN-PASSWORD or {env_name}_DSG_WEBDAV_ADMIN_PASSWORD found in APP subfolder.")
            print(f"Using best match: {best_match['reason']} in {best_match['path']}")
            return best_match['entry']
        
        # If no result found, print all credentials for debugging
        if not result and not found_entries:
            print("\nAll credentials found during search:")
            for cred in all_credentials:
                print(f"  - {cred['path']}: {cred['name']} (ID: {cred['id']})")
            
        return result

    def find_folder_id_by_name(self, folder_structure, search_name):
        if isinstance(folder_structure, dict):
            if folder_structure.get('Name') == search_name:
                return folder_structure.get('Id')
            
            children = folder_structure.get('Children', [])
            for child in children:
                if child.get('Name') == search_name:
                    return child.get('Id')
                
                result = self.find_folder_id_by_name(child, search_name)
                if result:
                    return result
        return None

    def get_subfolders(self, folder_structure):
        folders = []
        if isinstance(folder_structure, dict):
            children = folder_structure.get('Children', [])

            # Check if we have wrapper folders (like DEV-OPOS-01, PRD-OPOS-01)
            # If so, flatten by looking at their children instead
            has_wrapper_folders = False
            for child in children:
                child_name = child.get('Name', '')
                # Detect wrapper patterns: contains OPOS or similar patterns
                if '-OPOS-' in child_name or child_name.endswith('-01') or child_name.endswith('-02'):
                    has_wrapper_folders = True
                    break

            if has_wrapper_folders:
                # Flatten: get children of wrapper folders
                for wrapper in children:
                    wrapper_children = wrapper.get('Children', [])
                    for child in wrapper_children:
                        folders.append({
                            'name': child.get('Name'),
                            'id': child.get('Id'),
                            'parent_wrapper': wrapper.get('Name')  # Keep track of which wrapper this came from
                        })
            else:
                # Normal behavior: direct children
                for child in children:
                    folders.append({
                        'name': child.get('Name'),
                        'id': child.get('Id')
                    })
        return sorted(folders, key=lambda x: x['name'])

    def print_all_credentials(self, folder_structure, path=""):
        """Print all credentials in the folder structure for debugging"""
        if not isinstance(folder_structure, dict):
            return
            
        folder_name = folder_structure.get('Name', '')
        current_path = f"{path}/{folder_name}" if path else folder_name
        
        credentials = folder_structure.get('Credentials', [])
        for cred in credentials:
            cred_name = cred.get('Name', '')
            cred_id = cred.get('Id', '')
            print(f"  - {current_path}: {cred_name} (ID: {cred_id})")
            
        children = folder_structure.get('Children', [])
        for child in children:
            self.print_all_credentials(child, current_path)

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget (delegates to create_tooltip from utils)"""
        return create_tooltip(widget, text, parent_window=self.root)

        self.root.mainloop()

    def clear_keepass_credentials(self):
        """Clear stored KeePass credentials"""
        GKInstallBuilder.keepass_client = None
        GKInstallBuilder.keepass_username = None
        GKInstallBuilder.keepass_password = None
        
        # Update the button state if button exists
        if hasattr(self, 'keepass_button') and self.keepass_button:
            self.update_keepass_button()
        
        messagebox.showinfo("KeePass Credentials", "KeePass credentials have been cleared.")

    def open_launcher_editor(self):
        """Open the launcher settings editor"""
        self.launcher_editor.open_editor()
    
    def open_environment_manager(self):
        """Open the environment manager dialog"""
        self.environment_manager.open_manager()
        
    def generate_installation_files(self):
        """Generate installation files using the project generator"""
        try:
            # Update config from entries
            self.config_manager.update_config_from_entries()
            
            # Save the output directory in the config
            output_dir = self.config_manager.config.get("output_dir", "")
            if output_dir:
                print(f"Using output directory: {output_dir}")
                self.config_manager.config["output_dir"] = output_dir
                self.config_manager.save_config_silent()
            
            # Generate the installation files
            self.project_generator.generate(self.config_manager.config)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate installation files: {str(e)}")
            return

    def regenerate_configuration(self):
        """Regenerate configuration based on the base URL"""
        try:
            # Get the base URL entry directly
            base_url_entry = self.config_manager.get_entry("base_url")
            if not base_url_entry:
                self.show_error("Error", "Base URL entry not found.")
                return
                
            # Get the base URL value
            base_url = base_url_entry.get()
            if not base_url:
                self.show_error("Error", "Please enter a base URL first.")
                return
            
            # Update configuration based on the base URL
            self.auto_fill_based_on_url(base_url)
            
            # Show success message
            self.show_info("Success", "Configuration regenerated successfully based on the base URL.")
            
            # If we have sections that were hidden, show them now
            if hasattr(self, 'remaining_sections_created') and not self.remaining_sections_created:
                self.create_remaining_sections()
                self.remaining_sections_created = True
                
            # Make sure base URL entry events are properly bound
            base_url_entry.bind("<FocusOut>", self.on_base_url_changed)
            
        except Exception as e:
            self.show_error("Error", f"Failed to regenerate configuration: {str(e)}")
            print(f"Error in regenerate_configuration: {e}")

    def on_platform_changed(self):
        """Handle platform change (delegates to PlatformHandler)"""
        platform = self.platform_var.get()
        self.platform_handler.on_platform_changed(platform)

    def on_hostname_detection_changed(self):
        """Handler for when hostname detection checkbox is changed"""
        is_hostname_enabled = self.hostname_detection_var.get()
        self.config_manager.update_entry_value("use_hostname_detection", is_hostname_enabled)
        # Ensure detection config is updated and saved
        if "detection_config" in self.config_manager.config:
            detection_config = self.config_manager.config["detection_config"]
            detection_config["hostname_detection"] = detection_config.get("hostname_detection", {})
            # Optionally update detection config with the new value if needed
            # detection_config["hostname_detection"]["enabled"] = is_hostname_enabled
            self.detection_manager.set_config(detection_config)
            self.config_manager.config["detection_config"] = self.detection_manager.get_config()
        else:
            # Create default config if missing
            platform_type = self.config_manager.config.get("platform", "Windows")
            default_base_dir = "C:\\gkretail\\stations" if platform_type == "Windows" else "/usr/local/gkretail/stations"
            default_config = {
                "file_detection_enabled": True,
                "use_base_directory": True,
                "base_directory": default_base_dir,
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
                "hostname_detection": {}
            }
            self.detection_manager.set_config(default_config)
            self.config_manager.config["detection_config"] = self.detection_manager.get_config()
        self.config_manager.save_config()

    def on_file_detection_changed(self):
        """Handler for when file detection checkbox is changed"""
        is_file_enabled = self.file_detection_var.get()
        self.config_manager.update_entry_value("file_detection_enabled", is_file_enabled)
        if hasattr(self, 'detection_manager'):
            self.detection_manager.enable_file_detection(is_file_enabled)
        # Always update and save the full detection config
        if "detection_config" in self.config_manager.config:
            detection_config = self.config_manager.config["detection_config"]
            detection_config["file_detection_enabled"] = is_file_enabled
            self.detection_manager.set_config(detection_config)
            self.config_manager.config["detection_config"] = self.detection_manager.get_config()
        else:
            # Create default config if missing
            platform_type = self.config_manager.config.get("platform", "Windows")
            default_base_dir = "C:\\gkretail\\stations" if platform_type == "Windows" else "/usr/local/gkretail/stations"
            default_config = {
                "file_detection_enabled": is_file_enabled,
                "use_base_directory": True,
                "base_directory": default_base_dir,
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
                "hostname_detection": {}
            }
            self.detection_manager.set_config(default_config)
            self.config_manager.config["detection_config"] = self.detection_manager.get_config()
        self.config_manager.save_config()
        # If the detection settings window is open, update it
        if hasattr(self, 'detection_window') and self.detection_window is not None and self.detection_window.winfo_exists():
            for widget in self.detection_window.winfo_children():
                if isinstance(widget, ctk.CTkScrollableFrame):
                    for child in widget.winfo_children():
                        if isinstance(child, ctk.CTkTabview):
                            for tab in child.winfo_children():
                                for frame in tab.winfo_children():
                                    if isinstance(frame, ctk.CTkFrame):
                                        for label in frame.winfo_children():
                                            if isinstance(label, ctk.CTkLabel) and ("currently" in label.cget("text") and ("ENABLED" in label.cget("text") or "DISABLED" in label.cget("text"))):
                                                label.configure(text="Hostname detection is currently ENABLED" if self.hostname_detection_var.get() else "Hostname detection is currently DISABLED")
                                                label.configure(text_color="green" if self.hostname_detection_var.get() else "red")
                                                pass


    def _safe_grab_set(self, window):
        """Safely set grab on a window, handling potential Linux visibility issues"""
        try:
            # Make sure window is visible and updated
            window.update_idletasks()
            window.update()
            window.deiconify()
            window.focus_force()
            
            # Attempt to set grab
            window.grab_set()
        except Exception as e:
            print(f"Warning: Could not set grab on window: {e}")
            # Try again after a short delay
            window.after(200, lambda: self._safe_grab_set(window))

    def run(self):
        """Start the application main loop"""
        self.root.mainloop()

def main():
    app = GKInstallBuilder()
    app.run()

if __name__ == "__main__":
    main()