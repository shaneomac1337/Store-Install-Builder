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

    def open_detection_settings(self):
        """Open the detection settings window"""
        if self.detection_window is not None and self.detection_window.winfo_exists():
            self.detection_window.lift()
            self.detection_window.focus_force()
            return
            
        # Create a new window for detection settings
        self.detection_window = ctk.CTkToplevel(self.root)
        self.detection_window.title("Detection Settings")
        self.detection_window.geometry("1024x1024")
        self.detection_window.transient(self.root)
        
        # Force window update and wait for it to be visible before grabbing
        self.detection_window.update()
        
        # Add a short delay to ensure the window is fully mapped on Linux
        self.detection_window.after(100, lambda: self._safe_grab_set(self.detection_window))
        
        # Main frame with scrollbar
        main_frame = ctk.CTkScrollableFrame(self.detection_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Apply mousewheel binding for Linux scrolling
        bind_mousewheel_to_frame(main_frame)
        
        # Title and description
        ctk.CTkLabel(
            main_frame, 
            text="Detection Settings",
            font=("Helvetica", 16, "bold")
        ).pack(anchor="w", padx=10, pady=10)
        
        # Create a tabview for different detection settings sections
        tabview = ctk.CTkTabview(main_frame)
        tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        tab_environment = tabview.add("Environment Detection")
        tab_file_detection = tabview.add("File Detection")
        tab_regex = tabview.add("Hostname Detection")
        
        # ----- ENVIRONMENT DETECTION TAB -----
        
        ctk.CTkLabel(
            tab_environment,
            text="Multi-Environment Auto-Detection",
            font=("Helvetica", 14, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            tab_environment,
            text="Installation scripts automatically detect the correct environment (P, DEV, Q-001, etc.) for multi-tenant deployments.",
            wraplength=650
        ).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Environment count
        environments = self.config_manager.get_environments()
        env_count = len(environments)
        
        count_frame = ctk.CTkFrame(tab_environment)
        count_frame.pack(fill="x", padx=10, pady=10)
        
        env_count_label = ctk.CTkLabel(
            count_frame,
            text=f"Configured Environments: {env_count}",
            font=("Helvetica", 12, "bold"),
            text_color="#4a9eff" if env_count > 0 else "gray"
        )
        env_count_label.pack(anchor="w", padx=10, pady=5)
        
        if env_count > 0:
            # Show configured environments
            env_list_frame = ctk.CTkFrame(count_frame)
            env_list_frame.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(
                env_list_frame,
                text="Available Environments:",
                font=("Helvetica", 11, "bold")
            ).pack(anchor="w", padx=5, pady=(5, 2))
            
            for env in environments[:5]:  # Show first 5
                env_text = f"  • {env.get('alias', 'N/A'):10} - {env.get('name', 'N/A'):25} ({env.get('base_url', 'N/A')})"
                ctk.CTkLabel(
                    env_list_frame,
                    text=env_text,
                    font=("Courier", 10),
                    text_color="gray70",
                    anchor="w"
                ).pack(anchor="w", padx=5, pady=1)
            
            if env_count > 5:
                ctk.CTkLabel(
                    env_list_frame,
                    text=f"  ... and {env_count - 5} more",
                    font=("Courier", 10),
                    text_color="gray50",
                    anchor="w"
                ).pack(anchor="w", padx=5, pady=1)
            
            # Link to environment manager
            ctk.CTkButton(
                count_frame,
                text="Open Environment Manager",
                command=self.open_environment_manager,
                width=200,
                fg_color="#2b5f8f",
                hover_color="#1a4060"
            ).pack(anchor="w", padx=10, pady=10)
        else:
            ctk.CTkLabel(
                count_frame,
                text="No environments configured. Configure environments in the Environment Manager.",
                text_color="orange",
                wraplength=600
            ).pack(anchor="w", padx=10, pady=5)
        
        # Detection priority explanation
        priority_frame = ctk.CTkFrame(tab_environment)
        priority_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            priority_frame,
            text="Environment Detection Priority (Highest to Lowest):",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Check if hostname environment detection is enabled
        hostname_env_enabled = self.detection_manager.get_hostname_env_detection()
        
        if hostname_env_enabled:
            priorities = [
                ("1️⃣ CLI Parameter", "-Env <alias> or -Environment <name>", "User explicitly specifies environment via command line"),
                ("2️⃣ Hostname Detection", "Extracts environment prefix from hostname", "Parses first character from hostname (e.g., 'P1234-101' → 'P')"),
                ("3️⃣ File Detection", "Environment=<alias> in .station files", "Reads environment alias from station files (e.g., POS.station, WDM.station)"),
                ("4️⃣ Manual Input", "User prompt", "If all detection methods fail, user is prompted to select environment")
            ]
        else:
            priorities = [
                ("1️⃣ CLI Parameter", "-Env <alias> or -Environment <name>", "User explicitly specifies environment via command line"),
                ("2️⃣ File Detection", "Environment=<alias> in .station files", "Reads environment alias from station files (e.g., POS.station, WDM.station)"),
                ("3️⃣ Manual Input", "User prompt", "If all detection methods fail, user is prompted to select environment")
            ]
        
        for priority, method, description in priorities:
            priority_item_frame = ctk.CTkFrame(priority_frame)
            priority_item_frame.pack(fill="x", padx=10, pady=3)
            
            ctk.CTkLabel(
                priority_item_frame,
                text=priority,
                font=("Helvetica", 11, "bold"),
                width=150,
                anchor="w"
            ).pack(side="left", padx=5)
            
            detail_frame = ctk.CTkFrame(priority_item_frame, fg_color="transparent")
            detail_frame.pack(side="left", fill="x", expand=True, padx=5)
            
            ctk.CTkLabel(
                detail_frame,
                text=method,
                font=("Courier", 10),
                text_color="#4a9eff",
                anchor="w"
            ).pack(anchor="w")
            
            ctk.CTkLabel(
                detail_frame,
                text=description,
                font=("Helvetica", 9),
                text_color="gray60",
                anchor="w"
            ).pack(anchor="w")
        
        # File format example for environment
        env_format_frame = ctk.CTkFrame(tab_environment)
        env_format_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            env_format_frame,
            text="Station File Format Example (with Environment):",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        env_example_text = """StoreID=1234
WorkstationID=101
Environment=P"""
        
        env_example_textbox = ctk.CTkTextbox(env_format_frame, height=70, width=650)
        env_example_textbox.pack(fill="x", padx=10, pady=5)
        env_example_textbox.insert("1.0", env_example_text)
        env_example_textbox.configure(state="disabled")
        
        ctk.CTkLabel(
            env_format_frame,
            text="💡 Tip: Add 'Environment=<alias>' line to your station files for automatic environment detection!",
            font=("Helvetica", 10),
            text_color="#4a9eff",
            wraplength=630
        ).pack(anchor="w", padx=10, pady=(5, 10))
        
        # ----- FILE DETECTION TAB -----
        
        ctk.CTkLabel(
            tab_file_detection, 
            text="Configure file-based detection to extract store IDs and workstation IDs from station files.",
            wraplength=650
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            tab_file_detection, 
            text="File detection is used as a fallback when hostname detection fails or is disabled.",
            wraplength=650,
            text_color="gray70",
        ).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Enable/disable detection checkbox
        enable_frame = ctk.CTkFrame(tab_file_detection)
        enable_frame.pack(fill="x", padx=10, pady=5)
        
        # Create a BooleanVar for the detection option
        self.detection_var = ctk.BooleanVar(value=self.detection_manager.is_detection_enabled())
        
        # Get hostname detection status
        hostname_detection_enabled = self.hostname_detection_var.get()
        
        # No longer forcing file detection when hostname detection is enabled
        # (allowing independent configuration)
        
        # Create checkbox for detection
        self.detection_checkbox = ctk.CTkCheckBox(
            enable_frame, 
            text="Enable file-based detection",
            variable=self.detection_var,
            onvalue=True,
            offvalue=False
        )
        self.detection_checkbox.pack(anchor="w", padx=10, pady=10)
        
        # Add an explanatory label for the current settings
        if hostname_detection_enabled and self.detection_var.get():
            explanation_text = "Both hostname detection and file detection are enabled. If hostname detection fails, file detection will be used as a fallback."
        elif hostname_detection_enabled and not self.detection_var.get():
            explanation_text = "Hostname detection is enabled but file detection is disabled. If hostname detection fails, the user will be prompted for manual input."
        elif not hostname_detection_enabled and self.detection_var.get():
            explanation_text = "Hostname detection is disabled, but file detection is enabled. File detection will be used to extract store and workstation IDs."
        else:
            explanation_text = "Both hostname detection and file detection are disabled. Users will be prompted for manual input."
        
        explanation_label = ctk.CTkLabel(
            enable_frame,
            text=explanation_text,
            text_color="gray70",
            font=("Helvetica", 10),
            wraplength=650,
            justify="left"
        )
        explanation_label.pack(anchor="w", padx=10, pady=(0, 10))
        
        # File format description
        format_frame = ctk.CTkFrame(tab_file_detection)
        format_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            format_frame, 
            text="File Format Example:",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        example_text = """StoreID=1234
WorkstationID=101"""
        
        example_textbox = ctk.CTkTextbox(format_frame, height=50, width=650)
        example_textbox.pack(fill="x", padx=10, pady=5)
        example_textbox.insert("1.0", example_text)
        example_textbox.configure(state="disabled")
        
        # ----- HOSTNAME DETECTION TAB -----
        
        ctk.CTkLabel(
            tab_regex, 
            text="Configure regex patterns for extracting store IDs and workstation IDs from computer hostnames.",
            wraplength=650
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        hostname_status_frame = ctk.CTkFrame(tab_regex)
        hostname_status_frame.pack(fill="x", padx=10, pady=5)
        
        # Status of hostname detection
        hostname_status_text = "Hostname detection is currently ENABLED" if self.hostname_detection_var.get() else "Hostname detection is currently DISABLED"
        hostname_status_color = "green" if self.hostname_detection_var.get() else "red"
        
        ctk.CTkLabel(
            hostname_status_frame,
            text=hostname_status_text,
            text_color=hostname_status_color,
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=10)
        
        # Add note about where to change the setting
        ctk.CTkLabel(
            hostname_status_frame,
            text="You can change this setting in the main interface under 'Project Configuration'",
            text_color="gray70",
            font=("Helvetica", 10)
        ).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Add regex engine information
        regex_info_frame = ctk.CTkFrame(hostname_status_frame)
        regex_info_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            regex_info_frame,
            text="Regex Engine Information:",
            font=("Helvetica", 11, "bold"),
            text_color="#FF8C00"  # Orange color
        ).pack(anchor="w", padx=10, pady=(5, 0))
        
        ctk.CTkLabel(
            regex_info_frame,
            text="Linux: Uses POSIX Extended regex (grep -E). No lookahead/lookbehind, no \\d/\\w. Use [0-9] for digits.",
            text_color="#FF8C00",  # Orange color
            font=("Helvetica", 10),
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 2))
        
        ctk.CTkLabel(
            regex_info_frame,
            text="Windows: PowerShell uses .NET/Perl-style regex. Supports \\d, \\w, lookahead.",
            text_color="#FF8C00",  # Orange color
            font=("Helvetica", 10),
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 5))
        
        # Environment detection from hostname
        env_detection_frame = ctk.CTkFrame(tab_regex)
        env_detection_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            env_detection_frame,
            text="Environment Detection from Hostname",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(5, 5))
        
        # Create a BooleanVar for environment detection
        self.hostname_env_detection_var = ctk.BooleanVar(
            value=self.detection_manager.get_hostname_env_detection()
        )
        
        # Checkbox for environment detection
        env_detect_checkbox = ctk.CTkCheckBox(
            env_detection_frame,
            text="Enable Environment Detection from Hostname",
            variable=self.hostname_env_detection_var,
            command=self.on_env_detection_toggle,
            onvalue=True,
            offvalue=False
        )
        env_detect_checkbox.pack(anchor="w", padx=10, pady=5)
        
        # Explanation label
        ctk.CTkLabel(
            env_detection_frame,
            text="Automatically extracts environment prefix (e.g., 'P', 'Q', 'DEV') from hostname like P1234-101",
            text_color="gray70",
            font=("Helvetica", 10),
            wraplength=650,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(
            env_detection_frame,
            text="When enabled, hostname regex is automatically set to 3-group pattern:",
            text_color="gray70",
            font=("Helvetica", 10, "bold"),
            wraplength=650,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 2))
        
        # Show 3-group requirement
        groups_info = ctk.CTkFrame(env_detection_frame, fg_color="transparent")
        groups_info.pack(fill="x", padx=20, pady=(0, 5))
        
        ctk.CTkLabel(
            groups_info,
            text="• Group 1: Environment prefix (e.g., 'P', 'Q', 'DEV')\n• Group 2: Store ID (e.g., '1234')\n• Group 3: Workstation ID (e.g., '101')",
            text_color="gray70",
            font=("Helvetica", 9),
            justify="left",
            anchor="w"
        ).pack(anchor="w")
        
        # Example regex patterns
        ctk.CTkLabel(
            env_detection_frame,
            text="Example patterns:",
            text_color="#4a9eff",
            font=("Helvetica", 10, "bold"),
            justify="left"
        ).pack(anchor="w", padx=10, pady=(5, 2))
        
        examples_frame = ctk.CTkFrame(env_detection_frame, fg_color="transparent")
        examples_frame.pack(fill="x", padx=20, pady=(0, 5))
        
        ctk.CTkLabel(
            examples_frame,
            text="^([A-Z]+)([0-9]+)-([0-9]+)$  →  P1234-101\n^([A-Z]+)-([0-9]+)-([0-9]+)$  →  P-1234-101",
            text_color="gray60",
            font=("Courier", 9),
            justify="left",
            anchor="w"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            env_detection_frame,
            text="💡 Tip: Toggle the checkbox to automatically switch between 2-group and 3-group regex patterns",
            text_color="#4a9eff",
            font=("Helvetica", 10),
            wraplength=650,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(5, 10))
        
        # Group mapping configuration
        group_mapping_frame = ctk.CTkFrame(env_detection_frame)
        group_mapping_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        ctk.CTkLabel(
            group_mapping_frame,
            text="Regex Group Mapping (Advanced):",
            font=("Helvetica", 11, "bold"),
            text_color="#FF8C00"
        ).pack(anchor="w", padx=10, pady=(5, 5))
        
        ctk.CTkLabel(
            group_mapping_frame,
            text="Configure which regex capture group corresponds to each value.",
            text_color="gray70",
            font=("Helvetica", 9),
            wraplength=650
        ).pack(anchor="w", padx=10, pady=(0, 5))
        
        # Get current group mappings
        group_mappings = self.detection_manager.get_all_group_mappings()
        
        # Create a sub-frame for the dropdowns
        dropdowns_frame = ctk.CTkFrame(group_mapping_frame, fg_color="transparent")
        dropdowns_frame.pack(fill="x", padx=20, pady=5)
        
        # Environment group dropdown
        env_group_frame = ctk.CTkFrame(dropdowns_frame, fg_color="transparent")
        env_group_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(
            env_group_frame,
            text="Environment:",
            width=120,
            anchor="w"
        ).pack(side="left", padx=(0, 10))
        
        self.env_group_dropdown = ctk.CTkOptionMenu(
            env_group_frame,
            values=["1", "2", "3"],
            width=80
        )
        self.env_group_dropdown.set(str(group_mappings["env"]))
        self.env_group_dropdown.pack(side="left")
        
        ctk.CTkLabel(
            env_group_frame,
            text="(e.g., P, Q, DEV)",
            text_color="gray60",
            font=("Helvetica", 9)
        ).pack(side="left", padx=(10, 0))
        
        # Store group dropdown
        store_group_frame = ctk.CTkFrame(dropdowns_frame, fg_color="transparent")
        store_group_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(
            store_group_frame,
            text="Store ID:",
            width=120,
            anchor="w"
        ).pack(side="left", padx=(0, 10))
        
        self.store_group_dropdown = ctk.CTkOptionMenu(
            store_group_frame,
            values=["1", "2", "3"],
            width=80
        )
        self.store_group_dropdown.set(str(group_mappings["store"]))
        self.store_group_dropdown.pack(side="left")
        
        ctk.CTkLabel(
            store_group_frame,
            text="(e.g., 1234)",
            text_color="gray60",
            font=("Helvetica", 9)
        ).pack(side="left", padx=(10, 0))
        
        # Workstation group dropdown
        ws_group_frame = ctk.CTkFrame(dropdowns_frame, fg_color="transparent")
        ws_group_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(
            ws_group_frame,
            text="Workstation ID:",
            width=120,
            anchor="w"
        ).pack(side="left", padx=(0, 10))
        
        self.workstation_group_dropdown = ctk.CTkOptionMenu(
            ws_group_frame,
            values=["1", "2", "3"],
            width=80
        )
        self.workstation_group_dropdown.set(str(group_mappings["workstation"]))
        self.workstation_group_dropdown.pack(side="left")
        
        ctk.CTkLabel(
            ws_group_frame,
            text="(e.g., 101)",
            text_color="gray60",
            font=("Helvetica", 9)
        ).pack(side="left", padx=(10, 0))
        
        # Example note
        ctk.CTkLabel(
            group_mapping_frame,
            text="Example: For hostname '1234-P-101' with regex '^([0-9]+)-([A-Z])-([0-9]+)$', set Environment=2, Store=1, Workstation=3",
            text_color="#4a9eff",
            font=("Helvetica", 9),
            wraplength=650,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(5, 5))
        
        # --- Path configuration ---
        # Create a frame for path configuration options
        path_config_frame = ctk.CTkFrame(tab_file_detection)
        path_config_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            path_config_frame, 
            text="Path Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        # Create a RadioButton frame for path configuration approach
        approach_frame = ctk.CTkFrame(path_config_frame)
        approach_frame.pack(fill="x", padx=10, pady=5)
        
        # Create a variable for the approach selection
        self.path_approach_var = ctk.StringVar(
            value="base_dir" if self.detection_manager.is_using_base_directory() else "custom_paths"
        )
        
        # Create RadioButtons for the approach
        base_dir_radio = ctk.CTkRadioButton(
            approach_frame,
            text="Use base directory with standard file names",
            variable=self.path_approach_var,
            value="base_dir",
            command=self.update_detection_ui
        )
        base_dir_radio.pack(anchor="w", padx=10, pady=5)
        
        custom_paths_radio = ctk.CTkRadioButton(
            approach_frame,
            text="Use custom file paths for each component",
            variable=self.path_approach_var,
            value="custom_paths",
            command=self.update_detection_ui
        )
        custom_paths_radio.pack(anchor="w", padx=10, pady=5)
        
        # --- Base Directory Configuration ---
        self.base_dir_frame = ctk.CTkFrame(tab_file_detection)
        self.base_dir_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            self.base_dir_frame, 
            text="Base Directory Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        # Directory selection
        base_dir_select_frame = ctk.CTkFrame(self.base_dir_frame)
        base_dir_select_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            base_dir_select_frame,
            text="Base Directory:",
            width=120
        ).pack(side="left", padx=10)
        
        self.base_dir_entry = ctk.CTkEntry(base_dir_select_frame, width=400)
        self.base_dir_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Set current value if any
        current_base_dir = self.detection_manager.get_base_directory()
        if current_base_dir:
            self.base_dir_entry.insert(0, current_base_dir)
        else:
            # Set default based on platform
            platform = self.config_manager.config.get("platform", "Windows")
            if platform == "Windows":
                self.base_dir_entry.insert(0, "C:\\gkretail\\stations")
            else:  # Linux
                self.base_dir_entry.insert(0, "/usr/local/gkretail/stations")
        
        # Add browse button
        browse_dir_btn = ctk.CTkButton(
            base_dir_select_frame,
            text="Browse",
            width=70,
            command=self.browse_base_directory
        )
        browse_dir_btn.pack(side="left", padx=10)
        
        # Station files naming section - table for customizing filenames
        filenames_frame = ctk.CTkFrame(self.base_dir_frame)
        filenames_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            filenames_frame,
            text="Customize Station File Names (optional):",
            font=("Helvetica", 11)
        ).pack(anchor="w", padx=10, pady=5)
        
        # Create a simple table for component -> filename mapping
        self.filename_entries = {}
        components = ["POS", "WDM", "FLOW-SERVICE", "LPA-SERVICE", "STOREHUB-SERVICE"]
        
        for component in components:
            frame = ctk.CTkFrame(filenames_frame)
            frame.pack(fill="x", padx=10, pady=2)
            
            ctk.CTkLabel(
                frame, 
                text=f"{component}:",
                width=120
            ).pack(side="left", padx=10)
            
            entry = ctk.CTkEntry(frame, width=200)
            entry.pack(side="left", padx=10)
            
            # Set current value
            entry.insert(0, self.detection_manager.get_custom_filename(component))
            
            # Store entry reference
            self.filename_entries[component] = entry
        
        # Custom Paths Configuration
        self.custom_paths_frame = ctk.CTkFrame(tab_file_detection)
        self.custom_paths_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            self.custom_paths_frame, 
            text="Custom Paths Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        # Station file path entries for each component
        self.file_path_entries = {}
        
        for component in components:
            frame = ctk.CTkFrame(self.custom_paths_frame)
            frame.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(
                frame, 
                text=f"{component}:",
                width=120
            ).pack(side="left", padx=10)
            
            entry = ctk.CTkEntry(frame, width=400)
            entry.pack(side="left", padx=10, fill="x", expand=True)
            
            # Set current value if any - get raw path without base directory combination
            current_path = self.detection_manager.detection_config["detection_files"].get(component, "")
            if current_path:
                entry.insert(0, current_path)
            
            # Store entry reference
            self.file_path_entries[component] = entry
            
            # Add browse button
            browse_btn = ctk.CTkButton(
                frame,
                text="Browse",
                width=70,
                command=lambda c=component: self.browse_station_file(c)
            )
            browse_btn.pack(side="left", padx=10)
        
        # Initially update UI based on selected approach
        self.update_detection_ui()
        
        # ----- REGEX TAB -----
        # Create a frame for regex editing
        regex_frame = ctk.CTkFrame(tab_regex)
        regex_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title and description
        ctk.CTkLabel(
            regex_frame, 
            text="Hostname Detection Regex Editor",
            font=("Helvetica", 14, "bold")
        ).pack(anchor="w", padx=10, pady=10)
        
        ctk.CTkLabel(
            regex_frame, 
            text="Customize the regular expressions used to extract Store ID and Workstation ID from hostnames.",
            wraplength=650
        ).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Create a note about regex capture groups
        note_frame = ctk.CTkFrame(regex_frame)
        note_frame.pack(fill="x", padx=10, pady=5)
        
        # Show different instructions based on environment detection setting
        if self.hostname_env_detection_var.get():
            ctk.CTkLabel(
                note_frame,
                text="Important: Your regex must include exactly THREE capture groups:",
                font=("Helvetica", 11, "bold"),
                text_color="#FF8C00"  # Orange
            ).pack(anchor="w", padx=10, pady=(5, 0))
            
            ctk.CTkLabel(
                note_frame,
                text="1. First group captures the Environment (e.g., 'P', 'Q', 'DEV')\n2. Second group captures the Store ID/Number\n3. Third group captures the Workstation ID",
                justify="left"
            ).pack(anchor="w", padx=20, pady=(0, 5))
        else:
            ctk.CTkLabel(
                note_frame,
                text="Important: Your regex must include exactly TWO capture groups:",
                font=("Helvetica", 11, "bold"),
                text_color="#FF8C00"  # Orange
            ).pack(anchor="w", padx=10, pady=(5, 0))
            
            ctk.CTkLabel(
                note_frame,
                text="1. First group captures the Store ID/Number\n2. Second group captures the Workstation ID (usually 3 digits but can be different)",
                justify="left"
            ).pack(anchor="w", padx=20, pady=(0, 5))
        
        # Create two sections: one for Windows and one for Linux
        self.create_regex_editor(regex_frame, "Windows")
        self.create_regex_editor(regex_frame, "Linux")
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill="x", padx=10, pady=10)
        
        save_btn = ctk.CTkButton(
            buttons_frame,
            text="Save Settings",
            command=self.save_detection_settings
        )
        save_btn.pack(side="right", padx=10)
        
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            command=self.detection_window.destroy
        )
        cancel_btn.pack(side="right", padx=10)
    
    def create_regex_editor(self, parent_frame, platform):
        """Create a regex editor section for a specific platform"""
        # Create a frame for this platform
        platform_frame = ctk.CTkFrame(parent_frame)
        platform_frame.pack(fill="x", padx=10, pady=10)
        
        # Title
        ctk.CTkLabel(
            platform_frame,
            text=f"{platform} Hostname Detection",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        # Regex entry
        regex_frame = ctk.CTkFrame(platform_frame)
        regex_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            regex_frame,
            text="Regex Pattern:",
            width=120
        ).pack(side="left", padx=10)
        
        # Create entry for regex pattern
        regex_entry = ctk.CTkEntry(regex_frame, width=450)
        regex_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Get current regex value
        current_regex = self.detection_manager.get_hostname_regex(platform.lower())
        regex_entry.insert(0, current_regex)
        
        # Store entry reference in instance variable
        if platform.lower() == "windows":
            self.windows_regex_entry = regex_entry
        else:
            self.linux_regex_entry = regex_entry
        
        # Test section
        test_frame = ctk.CTkFrame(platform_frame)
        test_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            test_frame,
            text="Test Hostname:",
            width=120
        ).pack(side="left", padx=10)
        
        # Create entry for test hostname
        test_hostname_entry = ctk.CTkEntry(test_frame, width=200)
        test_hostname_entry.pack(side="left", padx=10)
        
        # Get current test hostname
        test_hostname_entry.insert(0, self.detection_manager.get_test_hostname())
        
        # Store entry reference
        if platform.lower() == "windows":
            self.windows_test_entry = test_hostname_entry
        else:
            self.linux_test_entry = test_hostname_entry
        
        # Test button
        test_btn = ctk.CTkButton(
            test_frame,
            text="Test Regex",
            width=100,
            command=lambda: self.test_regex(platform.lower())
        )
        test_btn.pack(side="left", padx=10)
        
        # Results frame
        results_frame = ctk.CTkFrame(platform_frame)
        results_frame.pack(fill="x", padx=10, pady=5)
        
        # Create a text widget to show results (taller only)
        results_text = ctk.CTkTextbox(results_frame, height=110, width=650)
        results_text.pack(fill="x", padx=10, pady=5)
        results_text.insert("1.0", "Test results will appear here...")
        results_text.configure(state="disabled")
        
        # Store text widget reference
        if platform.lower() == "windows":
            self.windows_results_text = results_text
        else:
            self.linux_results_text = results_text
    
    def test_regex(self, platform):
        """Test the regex pattern against a sample hostname"""
        try:
            # Get the regex pattern and hostname from the appropriate entries
            if platform == "windows":
                regex_pattern = self.windows_regex_entry.get()
                hostname = self.windows_test_entry.get()
                results_text = self.windows_results_text
            else:
                regex_pattern = self.linux_regex_entry.get()
                hostname = self.linux_test_entry.get()
                results_text = self.linux_results_text

                # Perl/PCRE regex detection (basic heuristics)
                perl_regex_detected = False
                # Perl delimiters
                if regex_pattern.strip().startswith('/') and regex_pattern.strip().endswith('/'):
                    perl_regex_detected = True
                # Named groups, Unicode classes, \K
                if '(?<' in regex_pattern or r'\p{' in regex_pattern or r'\K' in regex_pattern:
                    perl_regex_detected = True
                # Common Perl/PCRE shorthands not supported by POSIX grep
                if r'\d' in regex_pattern or r'\w' in regex_pattern or r'\s' in regex_pattern or r'\D' in regex_pattern or r'\W' in regex_pattern or r'\S' in regex_pattern:
                    perl_regex_detected = True

                if perl_regex_detected:
                    results_text.configure(state="normal")
                    results_text.delete("1.0", "end")
                    results_text.insert("1.0", "❌ Perl/PCRE-style regex detected!\n\nPerl/PCRE regex syntax (e.g. /pattern/, named groups, Unicode classes, \\d, \\w, \\s, etc.) is not supported for Linux detection or POSIX grep.\nPlease use standard POSIX-compatible regex syntax, e.g. [0-9], [A-Za-z], etc.")
                    results_text.configure(state="disabled")
                    return

            # Update the pattern and hostname in the detection manager
            self.detection_manager.set_hostname_regex(regex_pattern, platform)
            self.detection_manager.set_test_hostname(hostname)
            
            # Read live group mappings from dropdowns and update detection manager
            if hasattr(self, 'env_group_dropdown'):
                self.detection_manager.set_group_mapping('env', int(self.env_group_dropdown.get()))
            if hasattr(self, 'store_group_dropdown'):
                self.detection_manager.set_group_mapping('store', int(self.store_group_dropdown.get()))
            if hasattr(self, 'workstation_group_dropdown'):
                self.detection_manager.set_group_mapping('workstation', int(self.workstation_group_dropdown.get()))

            # Test the regex
            result = self.detection_manager.test_hostname_regex(hostname, platform)

            # Display the results
            results_text.configure(state="normal")
            results_text.delete("1.0", "end")

            if result["success"]:
                # Success case
                results_text.insert("1.0", f"✅ Match successful!\n\n")
                
                # Check if environment was extracted (3 groups)
                if "environment" in result and result["environment"]:
                    results_text.insert("end", f"🌎 Environment: {result['environment']}\n")
                    results_text.insert("end", "(3-group regex detected)\n\n")

                if platform == "windows":
                    results_text.insert("end", f"Store ID: {result['store_id']}\n")
                    if "store_number" in result:
                        results_text.insert("end", f"Extracted Store Number: {result['store_number']}\n")
                    results_text.insert("end", f"Workstation ID: {result['workstation_id']}\n")
                    if "is_valid_store" in result:
                        valid_indicator = "✅" if result["is_valid_store"] else "❌"
                        results_text.insert("end", f"{valid_indicator} Store ID format: " +
                                             ("Valid" if result["is_valid_store"] else "Invalid") + "\n")
                    if "is_valid_ws" in result:
                        valid_indicator = "✅" if result["is_valid_ws"] else "❌"
                        results_text.insert("end", f"{valid_indicator} Workstation ID format: " +
                                             ("Valid" if result["is_valid_ws"] else "Invalid") + "\n")
                else:
                    # Linux has more detailed results
                    results_text.insert("end", f"Store ID: {result['store_id']}\n")
                    results_text.insert("end", f"Workstation ID: {result['workstation_id']}\n")
                    # Add validation results
                    if "is_valid_store" in result:
                        valid_indicator = "✅" if result["is_valid_store"] else "❌"
                        results_text.insert("end", f"{valid_indicator} Store ID format: " +
                                             ("Valid" if result["is_valid_store"] else "Invalid") + "\n")
                    if "is_valid_ws" in result:
                        valid_indicator = "✅" if result["is_valid_ws"] else "❌"
                        results_text.insert("end", f"{valid_indicator} Workstation ID format: " +
                                             ("Valid" if result["is_valid_ws"] else "Invalid") + "\n")
            else:
                # Failure case
                results_text.insert("1.0", f"❌ Regex did not match!\n\n")
                if "error" in result:
                    results_text.insert("end", f"Error: {result['error']}\n")
                else:
                    results_text.insert("end", "The regex pattern did not match the hostname or didn't capture the required groups.")

            results_text.configure(state="disabled")

        except Exception as e:
            if platform == "windows":
                results_text = self.windows_results_text
            else:
                results_text = self.linux_results_text
            results_text.configure(state="normal")
            results_text.delete("1.0", "end")
            results_text.insert("1.0", f"❌ Error testing regex!\n\n{str(e)}")
            results_text.configure(state="disabled")

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

    def update_detection_ui(self):
        """Update the detection UI based on the selected approach"""
        is_base_dir = self.path_approach_var.get() == "base_dir"
        
        if is_base_dir:
            # Show base directory frame, hide custom paths frame
            self.base_dir_frame.pack(fill="x", padx=10, pady=10)
            self.custom_paths_frame.pack_forget()
        else:
            # Show custom paths frame, hide base directory frame
            self.base_dir_frame.pack_forget()
            self.custom_paths_frame.pack(fill="x", padx=10, pady=10)
    
    def on_env_detection_toggle(self):
        """Handle environment detection checkbox toggle"""
        if self.hostname_env_detection_var.get():
            # Environment detection enabled - check if current regex has 3 groups
            import re
            
            # Get current patterns
            windows_pattern = self.windows_regex_entry.get() if hasattr(self, 'windows_regex_entry') else ""
            linux_pattern = self.linux_regex_entry.get() if hasattr(self, 'linux_regex_entry') else ""
            
            # Count capture groups in current patterns
            def count_groups(pattern):
                try:
                    return re.compile(pattern).groups
                except:
                    return 0
            
            windows_groups = count_groups(windows_pattern)
            linux_groups = count_groups(linux_pattern)
            
            # If either pattern doesn't have 3 groups, auto-apply 3-group pattern
            if windows_groups != 3 or linux_groups != 3:
                from tkinter import messagebox
                response = messagebox.askyesno(
                    "Update Regex Pattern?",
                    "Environment detection requires a 3-group regex pattern.\n\n"
                    "Current pattern doesn't have 3 groups.\n\n"
                    "Would you like to automatically update to the example 3-group pattern?\n\n"
                    "Pattern: ^([A-Z]+)([0-9]+)-([0-9]+)$\n"
                    "Test Hostname: P1234-101"
                )
                if response:
                    self.apply_3group_pattern()
        else:
            # Environment detection disabled - revert to classic 2-group pattern
            self.apply_classic_2group_pattern()
    
    def apply_3group_pattern(self):
        """Apply example 3-group regex pattern to both Windows and Linux"""
        three_group_pattern = "^([A-Z]+)([0-9]+)-([0-9]+)$"
        test_hostname = "P1234-101"
        
        # Update Windows regex
        if hasattr(self, 'windows_regex_entry'):
            self.windows_regex_entry.delete(0, 'end')
            self.windows_regex_entry.insert(0, three_group_pattern)
        
        # Update Linux regex  
        if hasattr(self, 'linux_regex_entry'):
            self.linux_regex_entry.delete(0, 'end')
            self.linux_regex_entry.insert(0, three_group_pattern)
        
        # Update test hostnames
        if hasattr(self, 'windows_test_entry'):
            self.windows_test_entry.delete(0, 'end')
            self.windows_test_entry.insert(0, test_hostname)
        
        if hasattr(self, 'linux_test_entry'):
            self.linux_test_entry.delete(0, 'end')
            self.linux_test_entry.insert(0, test_hostname)
        
        # Update group mappings for 3-group pattern: Environment(1), Store(2), Workstation(3)
        if hasattr(self, 'env_group_dropdown'):
            self.env_group_dropdown.set("1")
        if hasattr(self, 'store_group_dropdown'):
            self.store_group_dropdown.set("2")
        if hasattr(self, 'workstation_group_dropdown'):
            self.workstation_group_dropdown.set("3")
        
        # Show success message
        from tkinter import messagebox
        messagebox.showinfo(
            "Pattern Applied",
            f"Applied 3-group pattern to both Windows and Linux:\n\nPattern: {three_group_pattern}\nTest Hostname: {test_hostname}\n\nGroup Mappings: Environment=1, Store=2, Workstation=3\n\nClick 'Test Regex' to verify it extracts:\n• Environment: P\n• Store ID: 1234\n• Workstation ID: 101"
        )
    
    def apply_classic_2group_pattern(self):
        """Apply classic 2-group regex pattern to both Windows and Linux"""
        two_group_pattern = "^([0-9]+)-([0-9]+)$"
        test_hostname = "1234-101"
        
        # Update Windows regex
        if hasattr(self, 'windows_regex_entry'):
            self.windows_regex_entry.delete(0, 'end')
            self.windows_regex_entry.insert(0, two_group_pattern)
        
        # Update Linux regex  
        if hasattr(self, 'linux_regex_entry'):
            self.linux_regex_entry.delete(0, 'end')
            self.linux_regex_entry.insert(0, two_group_pattern)
        
        # Update test hostnames
        if hasattr(self, 'windows_test_entry'):
            self.windows_test_entry.delete(0, 'end')
            self.windows_test_entry.insert(0, test_hostname)
        
        if hasattr(self, 'linux_test_entry'):
            self.linux_test_entry.delete(0, 'end')
            self.linux_test_entry.insert(0, test_hostname)
        
        # Update group mappings for 2-group pattern: Store(1), Workstation(2), Environment not used
        if hasattr(self, 'env_group_dropdown'):
            self.env_group_dropdown.set("1")  # Not used but set to 1 by default
        if hasattr(self, 'store_group_dropdown'):
            self.store_group_dropdown.set("1")
        if hasattr(self, 'workstation_group_dropdown'):
            self.workstation_group_dropdown.set("2")
        
        # Show success message
        from tkinter import messagebox
        messagebox.showinfo(
            "Pattern Reverted",
            f"Reverted to classic 2-group pattern for both Windows and Linux:\n\nPattern: {two_group_pattern}\nTest Hostname: {test_hostname}\n\nGroup Mappings: Store=1, Workstation=2\n\nClick 'Test Regex' to verify it extracts:\n• Store ID: 1234\n• Workstation ID: 101"
        )
    
    def browse_base_directory(self):
        """Browse for a base directory"""
        from tkinter import filedialog
        
        directory = filedialog.askdirectory(
            title="Select Base Directory for Station Files"
        )
        
        if directory:
            # Update entry
            self.base_dir_entry.delete(0, 'end')
            self.base_dir_entry.insert(0, directory)
    
    def browse_station_file(self, component):
        """Browse for a station file for the specified component"""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title=f"Select {component} station file",
            filetypes=[("Station Files", "*.station"), ("All Files", "*.*")]
        )
        
        if file_path:
            # Update entry
            self.file_path_entries[component].delete(0, 'end')
            self.file_path_entries[component].insert(0, file_path)
    
    def save_detection_settings(self):
        """Save detection settings"""
        # If hostname detection is enabled, force station detection to be enabled
        if self.hostname_detection_var.get():
            self.detection_var.set(True)
            
        # Update detection manager with new values
        self.detection_manager.enable_file_detection(self.detection_var.get())
        
        # Set base directory or custom paths based on selected approach
        is_base_dir = self.path_approach_var.get() == "base_dir"
        self.detection_manager.use_base_directory(is_base_dir)
        
        if is_base_dir:
            # Save base directory
            self.detection_manager.set_base_directory(self.base_dir_entry.get())
            
            # Save custom filenames
            for component, entry in self.filename_entries.items():
                self.detection_manager.set_custom_filename(component, entry.get())
        else:
            # Save custom file paths
            for component, entry in self.file_path_entries.items():
                self.detection_manager.set_file_path(component, entry.get())
        
        # Save regex settings if they exist
        try:
            # Windows regex
            if hasattr(self, 'windows_regex_entry'):
                self.detection_manager.set_hostname_regex(
                    self.windows_regex_entry.get(), 
                    "windows"
                )
            
            # Linux regex
            if hasattr(self, 'linux_regex_entry'):
                self.detection_manager.set_hostname_regex(
                    self.linux_regex_entry.get(),
                    "linux"
                )
            
            # Test hostname
            if hasattr(self, 'linux_test_entry'):
                self.detection_manager.set_test_hostname(self.linux_test_entry.get())
            elif hasattr(self, 'windows_test_entry'):
                self.detection_manager.set_test_hostname(self.windows_test_entry.get())
        except Exception as e:
            print(f"Error saving regex settings: {e}")
        
        # Save hostname environment detection setting
        if hasattr(self, 'hostname_env_detection_var'):
            self.detection_manager.set_hostname_env_detection(self.hostname_env_detection_var.get())
        
        # Save group mappings from dropdowns
        if hasattr(self, 'env_group_dropdown'):
            self.detection_manager.set_group_mapping('env', int(self.env_group_dropdown.get()))
        if hasattr(self, 'store_group_dropdown'):
            self.detection_manager.set_group_mapping('store', int(self.store_group_dropdown.get()))
        if hasattr(self, 'workstation_group_dropdown'):
            self.detection_manager.set_group_mapping('workstation', int(self.workstation_group_dropdown.get()))
        
        # Save to config
        self.config_manager.config["detection_config"] = self.detection_manager.get_config()
        self.config_manager.save_config()
        
        # Close window
        if self.detection_window:
            self.detection_window.destroy()
            
        messagebox.showinfo("Success", "Detection settings saved successfully.")

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

# New class for the Offline Package Creator window
class OfflinePackageCreator:
    def __init__(self, parent, config_manager, project_generator, parent_app=None):
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Offline Package Creator")
        self.window.geometry("1280x1176")  # Increased from 1000x800
        self.window.transient(parent)  # Set to be on top of the parent window
        
        # Add window close protocol handler
        self.window.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
        # Store references
        self.config_manager = config_manager
        self.project_generator = project_generator
        self.parent_app = parent_app  # Store reference to the parent application (GKInstallBuilder instance)
        
        # Register callback for platform changes
        if parent_app and hasattr(parent_app, 'platform_var'):
            parent_app.platform_var.trace_add("write", self.update_platform_info)
        
        # Create main frame with scrollbar
        self.main_frame = ctk.CTkScrollableFrame(self.window)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Apply mousewheel binding for Linux scrolling
        bind_mousewheel_to_frame(self.main_frame)
        
        # Create DSG API browser
        self.create_dsg_api_browser_ui()
        
        # Create offline package section
        self.create_offline_package_section()
    
    def on_window_close(self):
        """Handle window close event"""
        try:
            # Update config from entries
            self.config_manager.update_config_from_entries()
            
            # Clean up entries
            for entry in list(self.config_manager.entries):
                if hasattr(entry, 'widget') and entry.widget.winfo_toplevel() == self.window:
                    self.config_manager.unregister_entry(entry)
            
            # Release window grab and destroy
            self.window.grab_release()
            self.window.destroy()
            
            # Restore parent window and rebind events
            if self.parent_app:
                # Restore main window focus
                self.parent_app.window.focus_force()
                
                # Rebind base URL events
                base_url_entry = self.parent_app.config_manager.get_entry("base_url")
                if base_url_entry:
                    base_url_entry.bind("<FocusOut>", self.parent_app.on_base_url_changed)
                    
                # Ensure refresh button is properly set up
                if hasattr(self.parent_app, 'refresh_button'):
                    self.parent_app.refresh_button.configure(command=self.parent_app.regenerate_configuration)
                    
        except Exception as e:
            print(f"Error during offline creator cleanup: {e}")
        finally:
            # Ensure parent app reference is cleaned up
            if self.parent_app:
                self.parent_app.offline_creator = None
    
    def create_offline_package_section(self):
        # Create frame for offline package options
        self.offline_package_frame = ctk.CTkFrame(self.main_frame)
        self.offline_package_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        ctk.CTkLabel(
            self.offline_package_frame, 
            text="Create Offline Package",
            font=("Helvetica", 16, "bold")
        ).pack(pady=(10, 5), padx=10)
        
        # API connection prompt
        connection_frame = ctk.CTkFrame(self.offline_package_frame, fg_color="transparent")
        connection_frame.pack(pady=(0, 5), padx=10, fill="x")
        
        connection_icon = ctk.CTkLabel(
            connection_frame,
            text="ℹ️",
            font=("Helvetica", 12)
        )
        connection_icon.pack(side="left", padx=(5, 0))
        
        self.connection_prompt = ctk.CTkLabel(
            connection_frame,
            text="Connect to DSG API first to download components",
            font=("Helvetica", 12, "italic"),
            text_color="#8C8C8C"
        )
        self.connection_prompt.pack(side="left", padx=5)
        
        # Platform information
        platform = self.config_manager.config.get("platform", "Windows")
        platform_color = "#3a7ebf" if platform == "Windows" else "#2eb82e"  # Blue for Windows, Green for Linux
        platform_frame = ctk.CTkFrame(self.offline_package_frame, fg_color="transparent")
        platform_frame.pack(pady=(0, 10), padx=10)
        
        ctk.CTkLabel(
            platform_frame,
            text="Platform:",
            font=("Helvetica", 12)
        ).pack(side="left", padx=(0, 5))
        
        self.platform_info_label = ctk.CTkLabel(
            platform_frame,
            text=f"{platform} Selected",
            font=("Helvetica", 12, "bold"),
            text_color=platform_color
        )
        self.platform_info_label.pack(side="left")
        
        # Description
        ctk.CTkLabel(
            self.offline_package_frame, 
            text="Select components to include in the offline package:",
            font=("Helvetica", 12)
        ).pack(pady=(0, 10), padx=10)
        
        # Components frame
        self.components_frame = ctk.CTkFrame(self.offline_package_frame)
        self.components_frame.pack(fill="x", padx=10, pady=5)
        
        # Platform dependencies section
        platform_section_frame = ctk.CTkFrame(self.components_frame)
        platform_section_frame.pack(fill="x", pady=5, padx=10)
        
        # Platform section header
        ctk.CTkLabel(
            platform_section_frame,
            text="Platform Dependencies",
            font=("Helvetica", 12, "bold"),
            text_color=platform_color
        ).pack(anchor="w", pady=(5, 10), padx=10)
        
        # Platform components frame
        platform_components_frame = ctk.CTkFrame(platform_section_frame)
        platform_components_frame.pack(fill="x", pady=0, padx=10)
        
        # Java checkbox
        self.include_java = ctk.BooleanVar(value=False)
        java_checkbox = ctk.CTkCheckBox(
            platform_components_frame,
            text="Java",
            variable=self.include_java,
            checkbox_width=20,
            checkbox_height=20
        )
        java_checkbox.pack(side="left", pady=5, padx=10)
        
        # Tomcat checkbox
        self.include_tomcat = ctk.BooleanVar(value=False)
        tomcat_checkbox = ctk.CTkCheckBox(
            platform_components_frame,
            text="Tomcat",
            variable=self.include_tomcat,
            checkbox_width=20,
            checkbox_height=20
        )
        tomcat_checkbox.pack(side="left", pady=5, padx=20)
        
        # Jaybird checkbox
        self.include_jaybird = ctk.BooleanVar(value=False)
        jaybird_checkbox = ctk.CTkCheckBox(
            platform_components_frame,
            text="Jaybird",
            variable=self.include_jaybird,
            checkbox_width=20,
            checkbox_height=20
        )
        jaybird_checkbox.pack(side="left", pady=5, padx=20)
        
        # Application components section header
        app_section_header = ctk.CTkLabel(
            self.components_frame,
            text="Application Components",
            font=("Helvetica", 12, "bold")
        )
        app_section_header.pack(anchor="w", pady=(15, 5), padx=20)
        
        # Helper function to update dependencies when components are toggled
        def update_dependencies():
            # Check if any other application component (besides POS) is selected
            other_components_selected = (
                self.include_wdm.get() or 
                self.include_flow_service.get() or 
                self.include_lpa_service.get() or 
                self.include_storehub_service.get()
            )
            
            # Handle POS separately - it only affects Java
            if self.include_pos.get():
                self.include_java.set(True)
            elif not other_components_selected:
                # Only uncheck Java if no other components need it
                self.include_java.set(False)
                
            # Handle other components - they affect both Java and Tomcat
            if other_components_selected:
                self.include_java.set(True)
                self.include_tomcat.set(True)
            else:
                # Only uncheck Tomcat if no other components need it
                self.include_tomcat.set(False)
                
            # Handle StoreHub separately - it's the only one that needs Jaybird
            if self.include_storehub_service.get():
                self.include_jaybird.set(True)
            else:
                self.include_jaybird.set(False)
        
        # POS component frame
        pos_component_frame = ctk.CTkFrame(self.components_frame)
        pos_component_frame.pack(fill="x", pady=5, padx=10)
        
        # POS checkbox
        self.include_pos = ctk.BooleanVar(value=False)
        # Make sure initial dependency selection is set correctly
        
        # Add trace to POS variable
        self.include_pos.trace_add("write", lambda *args: update_dependencies())
        
        pos_checkbox = ctk.CTkCheckBox(
            pos_component_frame,
            text="POS",
            variable=self.include_pos,
            checkbox_width=20,
            checkbox_height=20
        )
        pos_checkbox.pack(side="left", pady=5, padx=10)
        
        # WDM component frame
        wdm_component_frame = ctk.CTkFrame(self.components_frame)
        wdm_component_frame.pack(fill="x", pady=5, padx=10)
        
        # WDM checkbox
        self.include_wdm = ctk.BooleanVar(value=False)
        # Add trace to WDM variable
        self.include_wdm.trace_add("write", lambda *args: update_dependencies())
        
        wdm_checkbox = ctk.CTkCheckBox(
            wdm_component_frame,
            text="WDM",
            variable=self.include_wdm,
            checkbox_width=20,
            checkbox_height=20
        )
        wdm_checkbox.pack(side="left", pady=5, padx=10)
        
        # Flow Service component frame
        flow_service_component_frame = ctk.CTkFrame(self.components_frame)
        flow_service_component_frame.pack(fill="x", pady=5, padx=10)
        
        # Flow Service checkbox
        self.include_flow_service = ctk.BooleanVar(value=False)
        # Add trace to Flow Service variable
        self.include_flow_service.trace_add("write", lambda *args: update_dependencies())
        
        flow_service_checkbox = ctk.CTkCheckBox(
            flow_service_component_frame,
            text="Flow Service",
            variable=self.include_flow_service,
            checkbox_width=20,
            checkbox_height=20
        )
        flow_service_checkbox.pack(side="left", pady=5, padx=10)
        
        # LPA Service component frame
        lpa_service_component_frame = ctk.CTkFrame(self.components_frame)
        lpa_service_component_frame.pack(fill="x", pady=5, padx=10)
        
        # LPA Service checkbox
        self.include_lpa_service = ctk.BooleanVar(value=False)
        # Add trace to LPA Service variable
        self.include_lpa_service.trace_add("write", lambda *args: update_dependencies())
        
        lpa_service_checkbox = ctk.CTkCheckBox(
            lpa_service_component_frame,
            text="LPA Service",
            variable=self.include_lpa_service,
            checkbox_width=20,
            checkbox_height=20
        )
        lpa_service_checkbox.pack(side="left", pady=5, padx=10)
        
        # StoreHub Service component frame
        storehub_service_component_frame = ctk.CTkFrame(self.components_frame)
        storehub_service_component_frame.pack(fill="x", pady=5, padx=10)
        
        # StoreHub Service checkbox
        self.include_storehub_service = ctk.BooleanVar(value=False)
        # Add trace to StoreHub Service variable
        self.include_storehub_service.trace_add("write", lambda *args: update_dependencies())
        
        storehub_service_checkbox = ctk.CTkCheckBox(
            storehub_service_component_frame,
            text="StoreHub Service",
            variable=self.include_storehub_service,
            checkbox_width=20,
            checkbox_height=20
        )
        storehub_service_checkbox.pack(side="left", pady=5, padx=10)
        
        # Call update_dependencies to set initial state based on default selections
        # Removed: update_dependencies()
        
        # Create button - initially disabled
        self.create_button = ctk.CTkButton(
            self.offline_package_frame,
            text="Create Offline Package",
            command=self.create_offline_package,
            fg_color="#6B7280",  # Gray color for disabled state
            hover_color="#858D9A",  # Slightly lighter gray for hover
            state="normal"  # We'll keep it enabled but use visual cues instead
        )
        self.create_button.pack(pady=10, padx=10)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.offline_package_frame,
            text="Please connect to DSG API before creating packages",
            font=("Helvetica", 12),
            text_color="#FF9E3D"  # Orange for warning
        )
        self.status_label.pack(pady=5, padx=10)
    
    def create_dsg_api_browser_ui(self):
        # Theme-aware color palette (light, dark)
        # Derive colors from the active CustomTkinter theme to avoid custom blue scheme
        theme = ctk.ThemeManager.theme
        mode = ctk.get_appearance_mode()
        pick = (lambda light, dark: light if mode == "Light" else dark)

        base_bg = pick(*theme["CTkFrame"]["fg_color"]) if isinstance(theme.get("CTkFrame", {}).get("fg_color"), (list, tuple)) else theme.get("CTkFrame", {}).get("fg_color", "transparent")
        label_fg = pick(*theme["CTkLabel"]["text_color"]) if isinstance(theme.get("CTkLabel", {}).get("text_color"), (list, tuple)) else theme.get("CTkLabel", {}).get("text_color", None)
        btn_fg = pick(*theme["CTkButton"]["fg_color"]) if isinstance(theme.get("CTkButton", {}).get("fg_color"), (list, tuple)) else theme.get("CTkButton", {}).get("fg_color", None)
        btn_hover = pick(*theme["CTkButton"]["hover_color"]) if isinstance(theme.get("CTkButton", {}).get("hover_color"), (list, tuple)) else theme.get("CTkButton", {}).get("hover_color", None)
        entry_bg = pick(*theme["CTkEntry"]["fg_color"]) if isinstance(theme.get("CTkEntry", {}).get("fg_color"), (list, tuple)) else theme.get("CTkEntry", {}).get("fg_color", None)
        entry_border = pick(*theme["CTkEntry"]["border_color"]) if isinstance(theme.get("CTkEntry", {}).get("border_color"), (list, tuple)) else theme.get("CTkEntry", {}).get("border_color", None)

        # Store colors as instance variable for access in other methods
        self._ui_colors = {
            'header_bg': base_bg,
            'path_bg': base_bg,
            'title_accent': label_fg,
            'muted_text': label_fg,
            'card_bg': base_bg,
            'primary': btn_fg,
            'primary_hover': btn_hover,
            'panel_bg': base_bg,
            'toolbar_bg': base_bg,
            'nav_btn': btn_fg,
            'nav_btn_hover': btn_hover,
            'nav_btn_disabled': ("#1E293B" if mode == "Dark" else "#D1D5DB"),
            'breadcrumb_bg': ("#1E293B" if mode == "Dark" else "#F1F5F9"),
            'breadcrumb_text': label_fg,
            'list_bg': base_bg,
            'list_fg': label_fg,
            'list_sel_bg': ("#334155" if mode == "Dark" else "#E2E8F0"),
            'list_sel_fg': label_fg,
            'menu_bg': base_bg,
            'menu_fg': label_fg,
            'menu_active_bg': ("#334155" if mode == "Dark" else "#E2E8F0"),
            'warning_text': ("#B45309", "#FF9E3D"),
            'status_badge_disconnected': ("#EF4444", "#FF6B6B"),
            'status_badge_warning': ("#F59E0B", "#F59E0B"),
            'status_badge_ok': ("#10B981", "#2ECC71"),
            'entry_bg': entry_bg,
            'entry_border': entry_border,
            'label_text': label_fg,
            'secondary_text': label_fg,
            'border_color': ("#334155" if mode == "Dark" else "#E2E8F0"),
            'separator_color': ("#1E293B" if mode == "Dark" else "#F1F5F9"),
        }
        colors = self._ui_colors  # Keep local reference for convenience

        # Create DSG API browser frame with theme defaults
        api_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        api_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Header section with border
        header_frame = ctk.CTkFrame(api_frame, fg_color=colors['header_bg'], corner_radius=10, border_width=2, border_color=colors['border_color'])
        header_frame.pack(fill="x", padx=0, pady=(0, 10))
        
        # Title section
        title_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_container.pack(fill="x", padx=15, pady=12)
        
        # Left side - Title with modern icon
        title_left = ctk.CTkFrame(title_container, fg_color="transparent")
        title_left.pack(side="left")
        
        icon_label = ctk.CTkLabel(
            title_left,
            text="🚀",
            font=("Helvetica", 20)
        )
        icon_label.pack(side="left", padx=(0, 8))
        
        title_label = ctk.CTkLabel(
            title_left,
            text="DSG Content API",
            font=("Helvetica", 18, "bold"),
            text_color=colors['title_accent']
        )
        title_label.pack(side="left")
        
        # Right side - Current path breadcrumb with border
        path_container = ctk.CTkFrame(title_container, fg_color=colors['breadcrumb_bg'], corner_radius=8, border_width=1, border_color=colors['border_color'])
        path_container.pack(side="right")
        
        ctk.CTkLabel(
            path_container,
            text="📁",
            font=("Helvetica", 14)
        ).pack(side="left", padx=(10, 5))
        
        self.path_label = ctk.CTkLabel(
            path_container,
            text="/SoftwarePackage",
            font=("Helvetica", 12),
            text_color=colors['muted_text']
        )
        self.path_label.pack(side="left", padx=(0, 10), pady=8)
        
        # Connection card with border
        connection_card = ctk.CTkFrame(api_frame, fg_color=colors['card_bg'], corner_radius=10, border_width=2, border_color=colors['border_color'])
        connection_card.pack(fill="x", padx=0, pady=(0, 10))
        
        # Info section with auto-generate checkbox
        info_frame = ctk.CTkFrame(connection_card, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=(12, 8))
        
        # Auto-generate token checkbox
        self.auto_generate_token = ctk.BooleanVar(value=True)
        auto_gen_checkbox = ctk.CTkCheckBox(
            info_frame,
            text="🔄 Auto-generate token from Security Config",
            variable=self.auto_generate_token,
            font=("Helvetica", 11, "bold"),
            text_color=colors['secondary_text'],
            fg_color=colors['primary'],
            hover_color=colors['primary_hover'],
            checkbox_width=20,
            checkbox_height=20
        )
        auto_gen_checkbox.pack(side="left")
        
        # Token section
        token_container = ctk.CTkFrame(connection_card, fg_color="transparent")
        token_container.pack(fill="x", padx=15, pady=(0, 12))
        
        # Token label
        token_label_frame = ctk.CTkFrame(token_container, fg_color="transparent")
        token_label_frame.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            token_label_frame,
            text="🔐",
            font=("Helvetica", 16)
        ).pack(side="left", padx=(0, 8))
        
        ctk.CTkLabel(
            token_label_frame,
            text="Bearer Token:",
            font=("Helvetica", 13, "bold"),
            text_color=colors['label_text']
        ).pack(side="left")
        
        # Token entry (read-only, auto-filled)
        self.bearer_token = ctk.CTkEntry(
            token_container,
            width=350,
            height=36,
            show="•",
            corner_radius=8,
            border_width=2,
            border_color=colors['entry_border'],
            fg_color=colors['entry_bg'],
            font=("Courier", 11)
        )
        self.bearer_token.pack(side="left", padx=(0, 10))
        
        # Load saved bearer token if available
        if self.config_manager.config.get("bearer_token"):
            self.bearer_token.insert(0, self.config_manager.config["bearer_token"])
        
        # Register bearer token with config manager
        self.config_manager.register_entry("bearer_token", self.bearer_token)
        
        # Connect button with theme styling
        connect_btn = ctk.CTkButton(
            token_container,
            text="⚡ Connect",
            width=110,
            height=36,
            corner_radius=8,
            fg_color=colors['primary'],
            hover_color=colors['primary_hover'],
            font=("Helvetica", 13, "bold"),
            command=self.connect_webdav
        )
        connect_btn.pack(side="left", padx=(0, 10))
        
        # Status badge
        self.status_badge = ctk.CTkFrame(
            token_container,
            fg_color=colors['status_badge_disconnected'],
            corner_radius=8,
            width=120,
            height=36
        )
        self.status_badge.pack(side="left")
        self.status_badge.pack_propagate(False)
        
        self.webdav_status = ctk.CTkLabel(
            self.status_badge,
            text="⚫ Disconnected",
            font=("Helvetica", 11, "bold"),
            text_color=("#000000", "#FFFFFF")
        )
        self.webdav_status.pack(expand=True)
        
        # Navigation and file browser container with border
        browser_main = ctk.CTkFrame(api_frame, fg_color=colors['panel_bg'], corner_radius=10, border_width=2, border_color=colors['border_color'])
        browser_main.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Navigation toolbar
        toolbar = ctk.CTkFrame(browser_main, fg_color=colors['toolbar_bg'], corner_radius=0, height=55)
        toolbar.pack(fill="x", padx=0, pady=0)
        toolbar.pack_propagate(False)
        
        # Separator line below toolbar
        toolbar_separator = ctk.CTkFrame(browser_main, fg_color=colors['separator_color'], height=2)
        toolbar_separator.pack(fill="x", padx=0, pady=0)
        
        # Navigation buttons container
        nav_buttons = ctk.CTkFrame(toolbar, fg_color="transparent")
        nav_buttons.pack(side="left", padx=12, pady=8)
        
        # Back button
        self.back_btn = ctk.CTkButton(
            nav_buttons,
            text="◄ Back",
            width=85,
            height=38,
            corner_radius=6,
            fg_color=colors['nav_btn'],
            hover_color=colors['nav_btn_hover'],
            font=("Segoe UI", 11, "bold"),
            border_width=1,
            border_color=colors['border_color'],
            command=self._navigate_back,
            state="disabled"
        )
        self.back_btn.pack(side="left", padx=(0, 6))
        
        # Refresh button
        self.refresh_btn = ctk.CTkButton(
            nav_buttons,
            text="⟳ Refresh",
            width=95,
            height=38,
            corner_radius=6,
            fg_color=colors['nav_btn'],
            hover_color=colors['nav_btn_hover'],
            font=("Segoe UI", 11, "bold"),
            border_width=1,
            border_color=colors['border_color'],
            command=self._refresh_current_directory
        )
        self.refresh_btn.pack(side="left")
        
        # Path breadcrumb display with subtle border
        breadcrumb_container = ctk.CTkFrame(toolbar, fg_color=colors['breadcrumb_bg'], corner_radius=6, height=38, border_width=1, border_color=colors['border_color'])
        breadcrumb_container.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        
        self.breadcrumb_label = ctk.CTkLabel(
            breadcrumb_container,
            text="/SoftwarePackage",
            font=("Consolas", 11),
            text_color=colors['breadcrumb_text'],
            anchor="w"
        )
        self.breadcrumb_label.pack(fill="x", padx=12, pady=8)
        
        # File list container with proper scrolling and padding
        list_container = ctk.CTkFrame(browser_main, fg_color=colors['panel_bg'], corner_radius=0)
        list_container.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Use standard tkinter Listbox for better performance with many items
        import tkinter as tk
        
        # Create frame for listbox and scrollbar with border and padding
        listbox_frame = tk.Frame(list_container, bg=colors['list_bg'], highlightbackground=colors['border_color'], highlightthickness=1, highlightcolor=colors['border_color'])
        listbox_frame.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(listbox_frame, bg=colors['nav_btn'], activebackground=colors['nav_btn_hover'], troughcolor=colors['panel_bg'])
        scrollbar.pack(side="right", fill="y")
        
        # Listbox with theme-aware styling and subtle borders
        self.file_listbox = tk.Listbox(
            listbox_frame,
            bg=colors['list_bg'],
            fg=colors['list_fg'],
            selectbackground=colors['list_sel_bg'],
            selectforeground=colors['list_sel_fg'],
            font=("Segoe UI", 11),
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            yscrollcommand=scrollbar.set,
            height=20,
            relief="flat"
        )
        self.file_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # Bind double-click, enter key, and right-click events
        self.file_listbox.bind("<Double-Button-1>", self._on_listbox_double_click)
        self.file_listbox.bind("<Return>", self._on_listbox_double_click)
        self.file_listbox.bind("<Button-3>", self._show_context_menu)  # Right-click
        
        # Create context menu
        import tkinter as tk
        self.context_menu = tk.Menu(self.file_listbox, tearoff=0, bg=colors['menu_bg'], fg=colors['menu_fg'], 
                                     activebackground=colors['menu_active_bg'], activeforeground=pick("#000000", "#FFFFFF"),
                                     borderwidth=1, relief="solid")
        self.context_menu.add_command(label="📂 Open Folder", command=self._context_open)
        self.context_menu.add_command(label="⬇ Download File", command=self._context_download)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Copy Path", command=self._context_copy_path)
        self.context_menu.add_command(label="📝 Copy Name", command=self._context_copy_name)
        self.context_menu.add_command(label="🔗 Copy Download URL", command=self._context_copy_download_url)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="⟳ Refresh", command=self._refresh_current_directory)
        self.context_menu.add_command(label="ℹ Properties", command=self._context_properties)
        
        # Store message label for loading/error states
        self.message_label = ctk.CTkLabel(
            list_container,
            text="",
            font=("Segoe UI", 13),
            text_color=colors['warning_text']
        )
        
        # Initialize browser state
        self._browser_state = {
            'current_path': '/SoftwarePackage',
            'loading': False,
            'connected': False,
            'items': [],
            'display_mode': 'list'  # list or message
        }
    
    def _clear_file_list(self):
        """Clear the file list"""
        self.file_listbox.delete(0, 'end')
        self._hide_message()
    
    def _show_message(self, icon, text, color="#64748B"):
        """Show a message overlay"""
        if self._browser_state.get('display_mode') != 'message':
            self.file_listbox.pack_forget()
            self.message_label.configure(text=f"{icon}  {text}", text_color=color)
            self.message_label.pack(expand=True, pady=80)
            self._browser_state['display_mode'] = 'message'
        else:
            # Just update the text without re-packing
            self.message_label.configure(text=f"{icon}  {text}", text_color=color)
    
    def _hide_message(self):
        """Hide message and show listbox"""
        if self._browser_state.get('display_mode') == 'message':
            self.message_label.pack_forget()
            self.file_listbox.pack(side="left", fill="both", expand=True)
            self._browser_state['display_mode'] = 'list'
    
    def _show_loading(self):
        """Show loading indicator"""
        if not self._browser_state['loading']:
            self._clear_file_list()
            self._browser_state['loading'] = True
            self._show_message("⟳", "Loading...", "#64748B")
            self.window.update_idletasks()
    
    def _show_empty_state(self):
        """Show empty directory state"""
        self._show_message("📂", "Empty Directory", "#64748B")
    
    def _show_error(self, error_message):
        """Show error state"""
        # Truncate long error messages
        display_msg = error_message if len(error_message) <= 60 else error_message[:57] + "..."
        self._show_message("⚠", f"Error: {display_msg}", "#EF4444")
    
    def _normalize_path(self, path):
        """Normalize path to use forward slashes and remove trailing slashes"""
        normalized = path.replace('\\', '/').rstrip('/')
        return normalized if normalized else '/SoftwarePackage'
    
    def _update_breadcrumb(self, path):
        """Update breadcrumb display"""
        self.breadcrumb_label.configure(text=path)
        self.path_label.configure(text=path)
        
        # Enable/disable back button with theme-aware colors
        if path in ['/', '/SoftwarePackage']:
            self.back_btn.configure(state="disabled", fg_color=self._ui_colors['nav_btn_disabled'])
        else:
            self.back_btn.configure(state="normal", fg_color=self._ui_colors['nav_btn'])
    
    def _load_directory(self, path):
        """Load and display directory contents"""
        if not hasattr(self, 'webdav') or not self.webdav or not self._browser_state['connected']:
            self._show_error("Not connected to DSG API")
            return
        
        # Normalize path
        path = self._normalize_path(path)
        
        # Check if already loading to prevent multiple requests
        if self._browser_state.get('loading'):
            return
        
        self._browser_state['current_path'] = path
        
        # Update UI - do breadcrumb first to avoid flicker
        self._update_breadcrumb(path)
        self._show_loading()
        
        try:
            # Fetch directory contents
            print(f"\n=== Loading Directory ===")
            print(f"Path: {path}")
            
            items = self.webdav.list_directories(path)
            
            print(f"Found: {len(items)} items")
            
            # Update state
            self._browser_state['items'] = items
            self._browser_state['loading'] = False
            
            # Clear loading and show items (minimize operations)
            self.file_listbox.delete(0, 'end')  # Clear directly without extra calls
            
            if not items:
                self._show_empty_state()
                return
            
            # Sort: directories first, then files alphabetically
            items.sort(key=lambda x: (not x['is_directory'], x['name'].lower()))
            
            # Populate listbox with color coding (batch update to reduce flicker)
            self._hide_message()
            
            # Disable updates during batch insert
            self.file_listbox.config(state='normal')
            
            for idx, item in enumerate(items):
                # Create display text with icon and determine color
                if item['is_directory']:
                    icon = "📁"
                    fg_color = "#60A5FA"  # Blue for folders
                elif item['name'].lower().endswith(('.zip', '.tar', '.gz', '.rar', '.7z')):
                    icon = "📦"
                    fg_color = "#A78BFA"  # Purple for archives
                elif item['name'].lower().endswith(('.exe', '.msi')):
                    icon = "⚙️"
                    fg_color = "#34D399"  # Green for executables - IMPORTANT
                elif item['name'].lower().endswith(('.jar', '.war')):
                    icon = "☕"
                    fg_color = "#FB923C"  # Orange for Java
                else:
                    icon = "📄"
                    fg_color = "#94A3B8"  # Gray for other files
                
                display_text = f"{icon}  {item['name']}"
                self.file_listbox.insert('end', display_text)
                
                # Apply color to this specific item
                self.file_listbox.itemconfig(idx, fg=fg_color)
            
            # Re-enable updates
            self.file_listbox.config(state='normal')
        
        except Exception as e:
            print(f"Error loading directory: {e}")
            import traceback
            traceback.print_exc()
            
            self._browser_state['loading'] = False
            self._show_error(str(e))
            
            # Update connection status
            if hasattr(self, 'webdav_status'):
                self.webdav_status.configure(text="⚠ Error")
                self.status_badge.configure(fg_color="#F59E0B")
    
    def _on_listbox_double_click(self, event=None):
        """Handle double-click on listbox item - open folders or download files"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index < len(self._browser_state['items']):
            item = self._browser_state['items'][index]
            if item.get('is_directory'):
                # Navigate into folder
                self._navigate_into(item['name'])
            else:
                # Download file to project root
                self._download_file_to_root(item)
    
    def _show_context_menu(self, event):
        """Show context menu on right-click"""
        # Select the item under cursor
        index = self.file_listbox.nearest(event.y)
        self.file_listbox.selection_clear(0, 'end')
        self.file_listbox.selection_set(index)
        self.file_listbox.activate(index)
        
        # Get the selected item
        if index < len(self._browser_state['items']):
            item = self._browser_state['items'][index]
            
            # Enable/disable menu items based on item type
            # Menu indices: 0=Open, 1=Download, 2=sep, 3=Copy Path, 4=Copy Name, 5=Copy URL, 6=sep, 7=Refresh, 8=Properties
            if item.get('is_directory'):
                self.context_menu.entryconfig(0, state="normal", label="📂 Open Folder")
                self.context_menu.entryconfig(1, state="disabled")
                # Enable Copy Download URL for folders (API browse URL) - index 5
                self.context_menu.entryconfig(5, state="normal", label="🔗 Copy API URL")
            else:
                self.context_menu.entryconfig(0, state="disabled")
                self.context_menu.entryconfig(1, state="normal", label="⬇ Download File")
                # Enable Copy Download URL for files - index 5
                self.context_menu.entryconfig(5, state="normal", label="🔗 Copy Download URL")
            
            # Show the menu
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
    
    def _context_open(self):
        """Context menu: Open folder"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self._browser_state['items']):
                item = self._browser_state['items'][index]
                if item.get('is_directory'):
                    self._navigate_into(item['name'])
    
    def _context_download(self):
        """Context menu: Download file"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self._browser_state['items']):
                item = self._browser_state['items'][index]
                if not item.get('is_directory'):
                    self._download_file_to_root(item)
    
    def _context_copy_path(self):
        """Context menu: Copy full path to clipboard"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self._browser_state['items']):
                item = self._browser_state['items'][index]
                full_path = f"{self._browser_state['current_path']}/{item['name']}".replace('//', '/')
                self.window.clipboard_clear()
                self.window.clipboard_append(full_path)
                print(f"Copied to clipboard: {full_path}")
    
    def _context_copy_name(self):
        """Context menu: Copy name to clipboard"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self._browser_state['items']):
                item = self._browser_state['items'][index]
                self.window.clipboard_clear()
                self.window.clipboard_append(item['name'])
                print(f"Copied to clipboard: {item['name']}")
    
    def _context_copy_download_url(self):
        """Context menu: Copy download URL to clipboard"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self._browser_state['items']):
                item = self._browser_state['items'][index]
                
                if item.get('is_directory'):
                    # For folders, copy the API browse URL
                    full_path = f"{self._browser_state['current_path']}/{item['name']}".replace('//', '/')
                    download_url = f"{self.webdav.base_url}/api/digital-content/services/rest/media/v1/files{full_path}"
                else:
                    # For files, get the actual download URL
                    remote_path = f"{self._browser_state['current_path']}/{item['name']}".replace('//', '/')
                    download_url = self.webdav.get_file_url(remote_path)
                
                self.window.clipboard_clear()
                self.window.clipboard_append(download_url)
                print(f"Copied download URL to clipboard: {download_url}")
                
                # Show success message
                from tkinter import messagebox
                messagebox.showinfo(
                    "URL Copied",
                    f"Download URL copied to clipboard!\n\n{download_url}"
                )
    
    def _context_properties(self):
        """Context menu: Show item properties"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self._browser_state['items']):
                item = self._browser_state['items'][index]
                
                # Create properties dialog
                from tkinter import messagebox
                
                item_type = "Folder" if item.get('is_directory') else "File"
                full_path = f"{self._browser_state['current_path']}/{item['name']}".replace('//', '/')
                
                props = [
                    f"Name: {item['name']}",
                    f"Type: {item_type}",
                    f"Path: {full_path}"
                ]
                
                if item.get('size'):
                    try:
                        # Convert to int if it's a string
                        size = int(item['size']) if isinstance(item['size'], str) else item['size']
                        size_mb = size / (1024 * 1024)
                        props.append(f"Size: {size_mb:.2f} MB ({size:,} bytes)")
                    except (ValueError, TypeError):
                        props.append(f"Size: {item['size']}")
                
                if item.get('mimeType'):
                    props.append(f"MIME Type: {item['mimeType']}")
                
                if item.get('lastModification'):
                    props.append(f"Last Modified: {item['lastModification']}")
                
                messagebox.showinfo("Properties", "\n".join(props))
    
    def _download_file_to_root(self, item):
        """Download a file to the downloaded_packages directory with progress dialog"""
        import os
        import requests
        from tkinter import messagebox
        import customtkinter as ctk
        import urllib3
        import threading
        
        # Suppress SSL warnings for faster downloads
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        try:
            # Get project root (parent of gk_install_builder)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Create downloaded_packages directory if it doesn't exist
            download_dir = os.path.join(project_root, "downloaded_packages")
            os.makedirs(download_dir, exist_ok=True)
            
            # Build full remote path
            remote_path = f"{self._browser_state['current_path']}/{item['name']}".replace('//', '/')
            
            # Local file path in downloaded_packages
            local_path = os.path.join(download_dir, item['name'])
            
            print(f"\n=== Downloading File ===")
            print(f"Remote: {remote_path}")
            print(f"Local: {local_path}")
            
            # Get download URL
            file_url = self.webdav.get_file_url(remote_path)
            headers = self.webdav._get_headers()
            
            # Create progress dialog
            progress_dialog = ctk.CTkToplevel(self.window)
            progress_dialog.title("Downloading File")
            progress_dialog.geometry("500x250")
            progress_dialog.transient(self.window)
            progress_dialog.grab_set()
            
            # Center the dialog
            x = self.window.winfo_x() + (self.window.winfo_width() // 2) - 250
            y = self.window.winfo_y() + (self.window.winfo_height() // 2) - 125
            progress_dialog.geometry(f"+{x}+{y}")
            
            # Track download cancellation
            download_cancelled = {'value': False}
            
            def on_dialog_close():
                """Handle dialog close - cancel download"""
                download_cancelled['value'] = True
                try:
                    progress_dialog.destroy()
                except:
                    pass
            
            progress_dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
            
            # Title
            ctk.CTkLabel(
                progress_dialog,
                text="⬇ Downloading File",
                font=("Segoe UI", 18, "bold")
            ).pack(pady=(20, 10))
            
            # Filename label
            filename_text = item['name']
            if item.get('size'):
                try:
                    size_mb = int(item['size']) / (1024 * 1024)
                    if size_mb < 1:
                        filename_text += f" ({int(item['size']) / 1024:.1f} KB)"
                    else:
                        filename_text += f" ({size_mb:.1f} MB)"
                except:
                    pass
            
            filename_label = ctk.CTkLabel(
                progress_dialog,
                text=filename_text,
                font=("Segoe UI", 12),
                wraplength=450
            )
            filename_label.pack(pady=(0, 20))
            
            # Progress bar
            progress_bar = ctk.CTkProgressBar(progress_dialog, width=450)
            progress_bar.pack(pady=10)
            progress_bar.set(0)
            
            # Status label
            status_label = ctk.CTkLabel(
                progress_dialog,
                text="Connecting to server...",
                font=("Segoe UI", 11)
            )
            status_label.pack(pady=5)
            
            # Size label
            size_label = ctk.CTkLabel(
                progress_dialog,
                text="0 MB / 0 MB",
                font=("Segoe UI", 10),
                text_color="#94A3B8"
            )
            size_label.pack(pady=5)
            
            # Info label for large files
            info_label = ctk.CTkLabel(
                progress_dialog,
                text="ℹ Large files may take longer to prepare on server",
                font=("Segoe UI", 9),
                text_color="#64748B"
            )
            info_label.pack(pady=(5, 0))
            
            progress_dialog.update()
            
            # Store download state
            download_state = {
                'error': None,
                'completed': False
            }
            
            # Background download function
            def download_thread():
                import time
                try:
                    # Update status safely with elapsed time
                    start_time = time.time()
                    timer_running = {'value': True}  # Flag to stop timer
                    
                    def update_wait_time():
                        if download_cancelled['value'] or not timer_running['value']:
                            return
                        elapsed = int(time.time() - start_time)
                        try:
                            if progress_dialog.winfo_exists():
                                status_label.configure(text=f"Requesting file from server... ({elapsed}s)")
                                progress_dialog.after(1000, update_wait_time)
                        except:
                            pass
                    
                    # Start timer updates
                    progress_dialog.after(0, lambda: (
                        status_label.configure(text="Requesting file from server... (0s)"),
                        progress_dialog.after(1000, update_wait_time)
                    ))
                    
                    # Download the file with token refresh on 401 and timeout
                    def make_download_request():
                        return requests.get(
                            file_url, 
                            headers=self.webdav._get_headers(), 
                            stream=True, 
                            verify=False,
                            timeout=(30, 60)  # 30s connection, 60s read - increased for large files
                        )
                    
                    response = self.webdav._handle_api_request(make_download_request)
                    
                    # Stop timer - download is starting
                    timer_running['value'] = False
                    
                    # Check if cancelled during request
                    if download_cancelled['value']:
                        return
                    
                    progress_dialog.after(0, lambda: status_label.configure(text="Starting download..."))
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = [0]  # Use list for mutable reference
                    
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            # Check if download was cancelled
                            if download_cancelled['value']:
                                print("Download cancelled by user")
                                return
                            
                            if chunk:
                                f.write(chunk)
                                downloaded[0] += len(chunk)
                                
                                # Update progress (throttle updates for performance)
                                if total_size > 0 and downloaded[0] % (8192 * 10) < 8192:
                                    progress = downloaded[0] / total_size
                                    downloaded_mb = downloaded[0] / (1024 * 1024)
                                    total_mb = total_size / (1024 * 1024)
                                    
                                    # Schedule GUI update on main thread
                                    try:
                                        progress_dialog.after(0, lambda p=progress, d=downloaded_mb, t=total_mb: (
                                            progress_bar.set(p),
                                            status_label.configure(text=f"Downloading... {p * 100:.1f}%"),
                                            size_label.configure(text=f"{d:.2f} MB / {t:.2f} MB")
                                        ))
                                    except:
                                        pass
                    
                    # Mark as completed
                    download_state['completed'] = True
                    
                except Exception as e:
                    download_state['error'] = e
                    import traceback
                    traceback.print_exc()
                finally:
                    # Close dialog on main thread
                    try:
                        progress_dialog.after(0, lambda: self._finish_download(
                            progress_dialog, download_state, download_cancelled, 
                            local_path, item, messagebox
                        ))
                    except:
                        pass
            
            # Start download in background thread
            thread = threading.Thread(target=download_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            # Error creating dialog or starting download
            print(f"Download initialization error: {e}")
            import traceback
            traceback.print_exc()
            
            self.status_label.configure(
                text=f"Download failed to start: {str(e)[:50]}",
                text_color="#FF6B6B"
            )
            
            messagebox.showerror(
                "Download Failed",
                f"Failed to start download:\n\n{str(e)}"
            )
    
    def _finish_download(self, progress_dialog, download_state, download_cancelled, local_path, item, messagebox):
        """Complete the download process - called from background thread via after()"""
        import os
        
        # Close progress dialog
        try:
            if progress_dialog.winfo_exists():
                progress_dialog.destroy()
        except:
            pass
        
        # Check if download was cancelled
        if download_cancelled['value']:
            # Delete partial file
            try:
                if os.path.exists(local_path):
                    os.remove(local_path)
                    print(f"Deleted partial file: {local_path}")
            except Exception as e:
                print(f"Could not delete partial file: {e}")
            
            # Update status
            self.status_label.configure(
                text=f"Download cancelled: {item['name']}",
                text_color="#FFA500"
            )
            print("Download cancelled by user")
            
            messagebox.showinfo(
                "Download Cancelled",
                f"Download was cancelled.\n\nPartial file has been removed."
            )
            return
        
        # Check for errors
        if download_state['error']:
            # Clean up partial file
            try:
                if os.path.exists(local_path):
                    os.remove(local_path)
                    print(f"Deleted partial file after error: {local_path}")
            except Exception as cleanup_err:
                print(f"Could not delete partial file: {cleanup_err}")
            
            # Show error
            self.status_label.configure(
                text=f"Download failed: {str(download_state['error'])[:50]}",
                text_color="#FF6B6B"
            )
            
            messagebox.showerror(
                "Download Failed",
                f"Failed to download file:\n\n{str(download_state['error'])}"
            )
            return
        
        # Success
        if download_state['completed']:
            self.status_label.configure(
                text=f"Downloaded {item['name']} to downloaded_packages",
                text_color="#53D86A"
            )
            print(f"Download complete: {local_path}")
            
            messagebox.showinfo(
                "Download Complete",
                f"File downloaded successfully!\n\nSaved to:\n{local_path}"
            )
    
    def _refresh_bearer_token(self):
        """Refresh the bearer token when it expires (called by DSGRestBrowser on 401)"""
        print("\n=== Refreshing Bearer Token ===")
        
        try:
            # Show token refresh in UI
            self.status_label.configure(
                text="🔄 Token expired - regenerating...",
                text_color="#FFA500"
            )
            self.webdav_status.configure(text="🔄 Refreshing...")
            self.status_badge.configure(fg_color="#FFA500")
            self.window.update_idletasks()
            
            # Generate new token using existing method
            base_url = self.config_manager.config["base_url"]
            new_token = self._generate_api_token_for_dsg(base_url)
            
            if new_token:
                # Update token in config and UI
                self.config_manager.config["bearer_token"] = new_token
                self.config_manager.save_config_silent()
                
                # Update token field if it exists
                if hasattr(self, 'bearer_token'):
                    self.bearer_token.delete(0, 'end')
                    self.bearer_token.insert(0, new_token)
                
                # Update status
                self.status_label.configure(
                    text="✅ Token refreshed automatically",
                    text_color="#53D86A"
                )
                self.webdav_status.configure(text="✅ Connected")
                self.status_badge.configure(fg_color="#2ECC71")
                
                # Show notification to user
                from tkinter import messagebox
                messagebox.showinfo(
                    "Token Refreshed",
                    "Your access token has expired and was automatically refreshed.\n\n"
                    "You can continue using the file browser normally."
                )
                
                print(f"Token refreshed successfully")
                return new_token
            else:
                # Token refresh failed
                self.status_label.configure(
                    text="❌ Token refresh failed",
                    text_color="#FF6B6B"
                )
                self.webdav_status.configure(text="❌ Failed")
                self.status_badge.configure(fg_color="#FF6B6B")
                self._browser_state['connected'] = False
                
                from tkinter import messagebox
                messagebox.showerror(
                    "Token Refresh Failed",
                    "Your access token has expired and could not be refreshed automatically.\n\n"
                    "Please check your Security Configuration and try connecting again."
                )
                
                print("Token refresh failed")
                return None
                
        except Exception as e:
            print(f"Error refreshing token: {e}")
            import traceback
            traceback.print_exc()
            
            self.status_label.configure(
                text="❌ Token refresh error",
                text_color="#FF6B6B"
            )
            self.webdav_status.configure(text="❌ Error")
            self.status_badge.configure(fg_color="#FF6B6B")
            self._browser_state['connected'] = False
            
            return None
    
    def _navigate_into(self, dirname):
        """Navigate into a subdirectory"""
        current = self._browser_state['current_path'].rstrip('/')
        new_path = f"{current}/{dirname}"
        
        print(f"Navigating: {current} -> {new_path}")
        
        self._load_directory(new_path)
    
    def _navigate_back(self):
        """Navigate to parent directory"""
        current = self._browser_state['current_path'].rstrip('/')
        
        if current in ['/', '/SoftwarePackage']:
            return
        
        # Get parent path
        parts = current.split('/')
        parent = '/'.join(parts[:-1]) if len(parts) > 1 else '/SoftwarePackage'
        
        if not parent or parent == '':
            parent = '/SoftwarePackage'
        
        print(f"Navigating back: {current} -> {parent}")
        
        self._load_directory(parent)
    
    def _refresh_current_directory(self):
        """Refresh the current directory"""
        current_path = self._browser_state.get('current_path', '/SoftwarePackage')
        print(f"Refreshing: {current_path}")
        self._load_directory(current_path)
    
    def refresh_listing(self):
        """Legacy method - redirects to new implementation"""
        self._refresh_current_directory()
    
    def on_item_click(self, item):
        """Legacy method - redirects to new implementation"""
        if item.get('is_directory'):
            self._navigate_into(item['name'])
    
    def connect_webdav(self):
        """Handle REST API connection with improved feedback"""
        base_url = self.config_manager.config["base_url"]
        bearer_token = self.bearer_token.get().strip() if hasattr(self, 'bearer_token') else None
        
        print("\n=== Connecting to DSG API ===")
        
        # Check if auto-generate is enabled
        auto_generate = self.auto_generate_token.get() if hasattr(self, 'auto_generate_token') else True
        
        if auto_generate:
            # Auto-generate mode: Always create fresh token
            print("Auto-generate enabled - generating fresh token")
            if bearer_token:
                print(f"Existing token in field (last 10 chars): ...{bearer_token[-10:]}")
            
            # Show generating token status
            self.webdav_status.configure(text="🔄 Generating token...")
            self.status_badge.configure(fg_color="#FFA500")
            self.window.update_idletasks()
            
            # Generate a fresh token
            bearer_token = self._generate_api_token_for_dsg(base_url)
            
            if not bearer_token:
                self.webdav_status.configure(text="❌ Failed")
                self.status_badge.configure(fg_color="#FF6B6B")
                messagebox.showerror("Authentication Failed",
                    "Could not generate authentication token.\n\n"
                    "💡 HINT: Please ensure Security Configuration is complete:\n\n"
                    "1. Basic Auth Password (launchpad_oauth2)\n"
                    "2. Form Password (eh_launchpad_password)\n"
                    "3. Base URL is correct\n\n"
                    "Or uncheck auto-generate and manually paste a Bearer token.")
                return
            
            print(f"New token generated (last 10 chars): ...{bearer_token[-10:]}")
            
            # Update the token field with the generated token
            if hasattr(self, 'bearer_token'):
                self.bearer_token.delete(0, 'end')
                self.bearer_token.insert(0, bearer_token)
        else:
            # Manual mode: Use token from field
            print("Auto-generate disabled - using manual token")
            if not bearer_token:
                self.webdav_status.configure(text="⚠️ No Token")
                self.status_badge.configure(fg_color="#FF6B6B")
                messagebox.showerror("No Token",
                    "Please enter a Bearer token in the token field.\n\n"
                    "Or enable 'Auto-generate token' to generate one automatically.")
                return
            
            print(f"Using manual token (last 10 chars): ...{bearer_token[-10:]}")
        
        if not base_url:
            self.webdav_status.configure(text="⚠️ No URL")
            self.status_badge.configure(fg_color="#FF6B6B")
            return
        
        # Show connecting status
        self.webdav_status.configure(text="🔌 Connecting...")
        self.status_badge.configure(fg_color="#FFA500")
        self.window.update_idletasks()
        
        # Create DSG REST API browser instance
        self.webdav = self.project_generator.create_dsg_api_browser(
            base_url,
            None,  # username not needed
            None,  # password not needed
            bearer_token
        )
        
        # Set up token refresh callback for automatic token renewal
        self.webdav.token_refresh_callback = self._refresh_bearer_token
        
        # Connect to DSG REST API
        success, message = self.webdav.connect()
        
        if success:
            self.webdav_status.configure(text="✅ Connected")
            self.status_badge.configure(fg_color="#2ECC71")
            
            # Save token to config
            if bearer_token:
                self.config_manager.config["bearer_token"] = bearer_token
            self.config_manager.save_config_silent()
            
            # Enable create offline package button with visual indicator (if it exists)
            if hasattr(self, 'create_button'):
                self.create_button.configure(
                    state="normal",
                    fg_color="#2B5BA0",  # Normal blue color
                    hover_color="#3A6AB0"  # Hover blue color
                )
            
            # Clear the connection prompt and update status label
            if hasattr(self, 'connection_prompt'):
                self.connection_prompt.configure(
                    text="DSG API connected successfully",
                    text_color="#53D86A"  # Green for success
                )
            
            # Update the status label
            self.status_label.configure(
                text="Ready to create offline packages",
                text_color="#53D86A"  # Green for success
            )
            
            # Update browser state and load initial directory
            self._browser_state['connected'] = True
            self._load_directory('/SoftwarePackage')
        else:
            self.webdav_status.configure(text="❌ Failed")
            self.status_badge.configure(fg_color="#FF6B6B")
            self._browser_state['connected'] = False
            
            # Show specific error in status label
            error_msg = message if len(message) < 50 else message[:47] + "..."
            self.status_label.configure(text=f"DSG API: {error_msg}", text_color="#FF6B6B")
            
            # If manual token mode and connection failed, offer to auto-generate
            if not auto_generate and bearer_token:
                # Check if it's a 401/authentication error
                if "401" in message or "Unauthorized" in message or "authentication" in message.lower():
                    response = messagebox.askyesno(
                        "Invalid or Expired Token",
                        "The provided Bearer token appears to be invalid or expired.\n\n"
                        "Would you like me to generate a new token automatically?\n\n"
                        "This will use your Security Configuration (OAuth2) to create a fresh token.",
                        icon='warning'
                    )
                    
                    if response:  # User clicked Yes
                        print("User requested auto-generation after failed manual token")
                        # Enable auto-generate and retry connection
                        self.auto_generate_token.set(True)
                        self.connect_webdav()
                        return
    
    def create_offline_package(self):
        """Create offline package with selected components"""
        try:
            # Check if DSG API is connected
            if not hasattr(self, 'webdav') or not getattr(self.webdav, 'connected', False):
                self.show_error("DSG API Connection Required", "Please connect to DSG API first before proceeding.")
                # Highlight the connect button with a pulsing effect
                self.webdav_status.configure(text="Not Connected", text_color="#FF6B6B")
                self.webdav_status.update()
                return
                
            # Check if at least one component is selected
            if not (self.include_pos.get() or 
                   self.include_wdm.get() or 
                   self.include_flow_service.get() or 
                   self.include_lpa_service.get() or 
                   self.include_storehub_service.get() or
                   self.include_java.get() or
                   self.include_tomcat.get() or
                   self.include_jaybird.get()):
                self.show_error("Error", "Please select at least one component")
                return
            
            # Get selected components and their dependencies
            selected_components = []
            platform_dependencies = {
                "JAVA": self.include_java.get(),
                "TOMCAT": self.include_tomcat.get(),
                "JAYBIRD": self.include_jaybird.get()
            }
            
            if self.include_pos.get():
                selected_components.append("POS")
                
            if self.include_wdm.get():
                selected_components.append("WDM")
            
            if self.include_flow_service.get():
                selected_components.append("FLOW-SERVICE")
                
            if self.include_lpa_service.get():
                selected_components.append("LPA-SERVICE")
                
            if self.include_storehub_service.get():
                selected_components.append("STOREHUB-SERVICE")
            
            # Update config with platform dependencies
            self.config_manager.config["platform_dependencies"] = platform_dependencies
            
            # Create offline package
            success, message = self.project_generator.prepare_offline_package(
                self.config_manager.config,
                selected_components,
                dialog_parent=self.window
            )
            
            if success:
                self.show_info("Success", message)
            else:
                self.show_error("Error", message)
                
        except Exception as e:
            self.show_error("Error", f"Failed to create offline package: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def show_error(self, title, message):
        """Show error dialog"""
        messagebox.showerror(title, message)

    def show_info(self, title, message):
        """Show info dialog"""
        messagebox.showinfo(title, message)

    def _generate_api_token_for_dsg(self, base_url):
        """Generate API bearer token for DSG REST API (same method as PPD/PPF)"""
        try:
            import base64
            import urllib.parse
            import requests
            import urllib3
            
            # Disable SSL warnings
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Get credentials from config (same as PPD/PPF)
            basic_auth_password = self.config_manager.config.get("launchpad_oauth2", "")
            form_password = self.config_manager.config.get("eh_launchpad_password", "")
            
            if not basic_auth_password or not form_password:
                print("Missing credentials for token generation")
                return None
            
            # Handle both base64 encoded and plain text passwords
            try:
                # Try to decode as base64 first
                basic_auth_password = base64.b64decode(basic_auth_password).decode('utf-8')
                form_password = base64.b64decode(form_password).decode('utf-8')
            except Exception:
                # Use the passwords as-is (they're already plain text)
                pass
            
            # Create Basic Auth header
            username = "launchpad"
            auth_string = f"{username}:{basic_auth_password}"
            auth_b64 = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
            
            # Prepare form data
            # Get username from config (same as PPD/PPF)
            form_username = self.config_manager.config.get("eh_launchpad_username", "1001")  # Fallback to 1001 if not set
            form_data_dict = {
                'username': form_username,
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
            
            print(f"Requesting OAuth token from: {token_url}")
            response = requests.post(token_url, headers=headers, data=form_data, timeout=30, verify=False)
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get('access_token')
                if access_token:
                    print("Bearer token generated successfully")
                    return access_token
            else:
                print(f"Token generation failed with status: {response.status_code}")
                print(f"Response: {response.text}")
            
            return None
            
        except Exception as e:
            print(f"Error generating bearer token: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_basic_auth_password_from_keepass(self, target_entry=None, password_type="basic_auth"):
        """Delegate to the parent app's get_basic_auth_password_from_keepass method"""
        # Use the stored reference to the parent app (GKInstallBuilder instance)
        if self.parent_app and hasattr(self.parent_app, 'get_basic_auth_password_from_keepass'):
            self.parent_app.get_basic_auth_password_from_keepass(target_entry=target_entry, password_type=password_type)
        else:
            # Show an error if the parent app doesn't have the method
            messagebox.showerror("Error", "Could not access KeePass integration from parent application.")
        
        # After successfully connecting to KeePass, update instance variables
        self.keepass_client = GKInstallBuilder.keepass_client
        self.keepass_username = GKInstallBuilder.keepass_username
        self.keepass_password = GKInstallBuilder.keepass_password
    
    def find_webdav_admin_password_entry(self, folder_structure):
        """Find Webdav Admin password entry in KeePass folder structure"""
        print("\nSearching for Webdav Admin password entry...")
        
        # Get all credentials
        all_credentials = self.keepass_client.get_all_credentials(folder_structure)
        
        # Filter credentials based on the entry name pattern
        matching_credentials = [
            cred for cred in all_credentials
            if cred['name'].startswith(f"{self.config_manager.config['env_name']}-DSG-WEBDAV-ADMIN-PASSWORD")
        ]
        
        if matching_credentials:
            # If multiple matching credentials found, print a warning
            if len(matching_credentials) > 1:
                print(f"Warning: Multiple matching credentials found for {self.config_manager.config['env_name']}-DSG-WEBDAV-ADMIN-PASSWORD")
                for cred in matching_credentials:
                    print(f"  - {cred['path']}: {cred['name']} (ID: {cred['id']})")
                print("Using the first matching credential.")
            
            # Return the first matching credential
            return matching_credentials[0]
        
        print(f"No matching credentials found for {self.config_manager.config['env_name']}-DSG-WEBDAV-ADMIN-PASSWORD")
        return None

    def update_platform_info(self, *args):
        """Update platform information label"""
        # Check if the window and label still exist
        try:
            if hasattr(self, 'platform_info_label') and self.platform_info_label.winfo_exists():
                platform = self.parent_app.platform_var.get()
                platform_color = "#3a7ebf" if platform == "Windows" else "#2eb82e"  # Blue for Windows, Green for Linux
                self.platform_info_label.configure(text=f"{platform} Selected", text_color=platform_color)
        except Exception as e:
            # Silently ignore errors when updating the label
            print(f"Warning: Could not update platform info label: {e}")

    def on_item_double_click(self, event):
        """Handle double click on an item in the listbox"""
        # Get the selected index
        selection = self.dir_list.curselection()
        if not selection:
            return
            
        index = selection[0]
        
        # Get the corresponding item
        if index < len(self.current_items):
            item = self.current_items[index]
            if item['is_directory']:
                self.enter_directory(item['name'])
    
    def enter_directory(self, dirname):
        """Legacy method - redirects to new implementation"""
        self._navigate_into(dirname)
    
    def navigate_up(self):
        """Legacy method - redirects to new implementation"""
        self._navigate_back()
    
    def handle_item_click(self, name, is_directory):
        """Handle clicking on an item in the directory listing"""
        if is_directory:
            self.enter_directory(name)

    def toggle_password_visibility(self):
        """Toggle password visibility between shown and hidden"""
        if self.password_visible:
            # Hide the password
            self.webdav_password.configure(show="•")
            self.password_toggle_btn.configure(text="👁️")
            self.password_visible = False
        else:
            # Show the password
            self.webdav_password.configure(show="")
            self.password_toggle_btn.configure(text="🔒")
            self.password_visible = True

def main():
    app = GKInstallBuilder()
    app.run()

if __name__ == "__main__":
    main()