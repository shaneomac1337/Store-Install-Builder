import customtkinter as ctk
import os
import tkinter.ttk as ttk
import tkinter as tk
from tkinter import messagebox
import sys
import requests
import json

# Support both package imports (for PyInstaller) and direct imports (for dev)
try:
    from gk_install_builder.config import ConfigManager
    from gk_install_builder.generator import ProjectGenerator
    from gk_install_builder.detection import DetectionManager
    from gk_install_builder.environment_manager import EnvironmentManager
    from gk_install_builder.pleasant_password_client import PleasantPasswordClient
    from gk_install_builder.ui.helpers import bind_mousewheel_to_frame
    from gk_install_builder.utils.tooltips import create_tooltip
    from gk_install_builder.utils.ui_colors import get_theme_colors
    from gk_install_builder.dialogs.about import AboutDialog
    from gk_install_builder.dialogs.launcher_settings import LauncherSettingsEditor
    from gk_install_builder.dialogs.offline_package import OfflinePackageCreator
    from gk_install_builder.dialogs.detection_settings import DetectionSettingsDialog
    from gk_install_builder.features.auto_fill import AutoFillManager
    from gk_install_builder.features.platform_handler import PlatformHandler
    from gk_install_builder.features.version_manager import VersionManager
    from gk_install_builder.features.certificate_manager import CertificateManager
    from gk_install_builder.integrations.api_client import APIClient
    from gk_install_builder.integrations.keepass_handler import KeePassHandler
except ImportError:
    from config import ConfigManager
    from generator import ProjectGenerator
    from detection import DetectionManager
    from environment_manager import EnvironmentManager
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from pleasant_password_client import PleasantPasswordClient
    from ui.helpers import bind_mousewheel_to_frame
    from utils.tooltips import create_tooltip
    from utils.ui_colors import get_theme_colors
    from gk_install_builder.dialogs.about import AboutDialog
    from gk_install_builder.dialogs.launcher_settings import LauncherSettingsEditor
    from gk_install_builder.dialogs.offline_package import OfflinePackageCreator
    from gk_install_builder.dialogs.detection_settings import DetectionSettingsDialog
    from gk_install_builder.features.auto_fill import AutoFillManager
    from gk_install_builder.features.platform_handler import PlatformHandler
    from gk_install_builder.features.version_manager import VersionManager
    from gk_install_builder.features.certificate_manager import CertificateManager
    from gk_install_builder.integrations.api_client import APIClient
    from gk_install_builder.integrations.keepass_handler import KeePassHandler

class GKInstallBuilder:
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

        # Create launcher settings editor
        self.launcher_editor = LauncherSettingsEditor(self.root, self.config_manager, self.project_generator)

        # Create environment manager
        self.environment_manager = EnvironmentManager(self.root, self.config_manager, self)

        # Initialize refactored feature modules
        self.auto_fill_manager = AutoFillManager(self.config_manager)
        self.platform_handler = PlatformHandler(self.config_manager)
        self.api_client = APIClient(self.root, self.config_manager)
        self.keepass_handler = KeePassHandler(self.root, self.config_manager)
        self.certificate_manager = CertificateManager(self.root, self.config_manager, self)

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

        # Initialize version manager now that main_frame exists
        self.version_manager = VersionManager(self.root, self.config_manager, self.api_client, self.main_frame)

        # Apply mousewheel binding for Linux scrolling
        bind_mousewheel_to_frame(self.main_frame)
        
        # Add version/info label at the top right of the main frame
        info_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        info_frame.pack(fill="x", pady=(0, 10))
        
        # Info button styled to match customtkinter aesthetics
        info_button = ctk.CTkButton(
            info_frame,
            text="i",
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
        self.create_tooltip(info_button, "About GK Install Builder")
        
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
                entry.bind("<KeyRelease>", lambda event: self.version_manager.on_project_version_change())
                entry.bind("<FocusOut>", lambda event: self.version_manager.on_project_version_change())
                entry.bind("<Return>", lambda event: self.version_manager.on_project_version_change())
                entry.bind("<Control-v>", lambda event: self.root.after(10, self.version_manager.on_project_version_change))
        
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

        # Add API Version Selection
        api_version_frame = ctk.CTkFrame(form_frame)
        api_version_frame.pack(fill="x", padx=10, pady=5)

        api_version_label = ctk.CTkLabel(api_version_frame, text="API Version:", width=150)
        api_version_label.pack(side="left", padx=10)

        # Create tooltip for API version
        self.create_tooltip(api_version_label, "Select API version based on your cloud platform version.\nLegacy (5.25): Uses /cims/, /config-service/, /swee-sdc/ endpoints\nNew (5.27+): Uses /api/ prefix for all endpoints")

        # Create a StringVar for the API version option
        self.api_version_var = ctk.StringVar(value=self.config_manager.config.get("api_version", "new"))

        # Create radio button frame for API version
        api_radio_frame = ctk.CTkFrame(api_version_frame)
        api_radio_frame.pack(side="left", padx=10)

        legacy_api_radio = ctk.CTkRadioButton(
            api_radio_frame,
            text="Legacy (5.25)",
            variable=self.api_version_var,
            value="legacy",
            command=lambda: self.config_manager.schedule_save()
        )
        legacy_api_radio.pack(side="left", padx=10)

        new_api_radio = ctk.CTkRadioButton(
            api_radio_frame,
            text="New (5.27+)",
            variable=self.api_version_var,
            value="new",
            command=lambda: self.config_manager.schedule_save()
        )
        new_api_radio.pack(side="left", padx=10)

        # Register the API version variable with config manager
        self.config_manager.register_entry("api_version", self.api_version_var)

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

        # Register detection variables with config manager
        self.config_manager.register_entry("use_hostname_detection", self.hostname_detection_var)
        self.config_manager.register_entry("file_detection_enabled", self.file_detection_var)

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

        # Installer Overrides section
        overrides_frame = ctk.CTkFrame(form_frame)
        overrides_frame.pack(fill="x", padx=10, pady=5)

        overrides_label = ctk.CTkLabel(
            overrides_frame,
            text="Installer Overrides:",
            width=150
        )
        overrides_label.pack(side="left", padx=10)

        self.installer_overrides_var = ctk.BooleanVar(value=self.config_manager.config.get("installer_overrides_enabled", True))
        installer_overrides_checkbox = ctk.CTkCheckBox(
            overrides_frame,
            text="Include installer overrides",
            variable=self.installer_overrides_var,
            onvalue=True,
            offvalue=False,
            command=self.on_installer_overrides_changed
        )
        installer_overrides_checkbox.pack(side="left", padx=10)
        self.create_tooltip(installer_overrides_checkbox,
            "When enabled, installer override XML files are included in the output package.\n"
            "Use the checkboxes below to configure which installation steps are skipped.\n"
            "You can edit the XMLs in helper/overrides/ after generation.")

        self.config_manager.register_entry("installer_overrides_enabled", self.installer_overrides_var)

        overrides_configure_btn = ctk.CTkButton(
            overrides_frame,
            text="Configure",
            width=100,
            command=self.open_overrides_settings
        )
        overrides_configure_btn.pack(side="left", padx=10)
        self.create_tooltip(overrides_configure_btn,
            "Select which components should receive installer override files.")

        # Override property checkboxes (sub-options)
        override_props_frame = ctk.CTkFrame(form_frame)
        override_props_frame.pack(fill="x", padx=10, pady=(0, 5))

        spacer = ctk.CTkLabel(override_props_frame, text="", width=150)
        spacer.pack(side="left", padx=10)

        override_props = self.config_manager.config.get("installer_overrides_properties", {
            "check-alive": True, "start-application": False, "start-updater": False,
        })

        self.override_check_alive_var = ctk.BooleanVar(value=override_props.get("check-alive", True))
        check_alive_cb = ctk.CTkCheckBox(
            override_props_frame,
            text="Skip health check (check-alive)",
            variable=self.override_check_alive_var,
            onvalue=True, offvalue=False,
            command=self.on_override_properties_changed
        )
        check_alive_cb.pack(side="left", padx=10)
        self.create_tooltip(check_alive_cb, "Skip the health check during component installation.")

        self.override_start_app_var = ctk.BooleanVar(value=override_props.get("start-application", False))
        start_app_cb = ctk.CTkCheckBox(
            override_props_frame,
            text="Skip start application",
            variable=self.override_start_app_var,
            onvalue=True, offvalue=False,
            command=self.on_override_properties_changed
        )
        start_app_cb.pack(side="left", padx=10)
        self.create_tooltip(start_app_cb, "Skip starting the application after installation.")

        self.remove_overrides_var = ctk.BooleanVar(value=self.config_manager.config.get("remove_overrides_after_install", False))
        remove_overrides_cb = ctk.CTkCheckBox(
            override_props_frame,
            text="Remove overrides after install",
            variable=self.remove_overrides_var,
            onvalue=True, offvalue=False,
            command=self.on_remove_overrides_changed
        )
        remove_overrides_cb.pack(side="left", padx=10)
        self.create_tooltip(remove_overrides_cb,
            "Remove the installer overrides folder after installation completes.\n"
            "If overrides are kept, Employee Hub update logic will also apply them\n"
            "(e.g. skipping check-alive, start-application) on future updates.\n"
            "Enable this to only use overrides for the initial install.")
        self.config_manager.register_entry("remove_overrides_after_install", self.remove_overrides_var)

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
            self.version_manager.create_component_versions()
        
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
                "OneX POS System Type",
                "WDM System Type",
                "Flow Service System Type",
                "LPA Service System Type",
                "StoreHub Service System Type",
                "RCS System Type",
                "Firebird Server Path"
            ]
            
            # Field tooltips for this section
            tooltips = {
                "Base Install Directory": "Root directory where components will be installed (e.g., 'C:\\gkretail' for Windows or '/usr/local/gkretail' for Linux)",
                "Tenant ID": "Tenant identifier for multi-tenant environments (e.g., '001')",
                "POS System Type": "Type of Point of Sale system (e.g., 'CSE-OPOS-CLOUD')",
                "OneX POS System Type": "Type of OneX POS Client system (e.g., 'CSE-OPOS-ONEX-CLOUD')",
                "Flow Service System Type": "Type of Flow Service (e.g., 'CSE-FlowService')",
                "LPA Service System Type": "Type of LPA Service (e.g., 'CSE-LPA-Service')",
                "StoreHub Service System Type": "Type of StoreHub Service (e.g., 'CSE-StoreHub-Service')",
                "RCS System Type": "Type of RCS Service (e.g., 'GKR-Resource-Cache-Service')",
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
                # Set password entry in keepass_handler
                self.keepass_handler.set_password_entries(basic_auth_entry=entry)
                ctk.CTkButton(
                    field_frame,
                    text="🔑",  # Key icon
                    width=40,
                    command=lambda: self.keepass_handler.get_basic_auth_password_from_keepass(password_type="basic_auth")
                ).pack(side="left", padx=5)
            elif field == "Webdav Admin":
                self.webdav_admin_password_entry = entry  # Store reference to this entry
                # Set password entry in keepass_handler
                self.keepass_handler.set_password_entries(webdav_admin_entry=entry)
                ctk.CTkButton(
                    field_frame,
                    text="🔑",  # Key icon
                    width=40,
                    command=lambda: self.keepass_handler.get_basic_auth_password_from_keepass(password_type="webdav_admin")
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
            self.certificate_manager.create_certificate_section(section_frame)
        
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

    def update_keepass_button(self):
        """Update the KeePass button state (delegates to KeePassHandler)"""
        self.keepass_handler.update_keepass_button()

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
            self.file_detection_var,
            parent_app=self
        )
        dialog.show()

    def test_default_versions_api(self):
        """Test the API to fetch default versions (delegates to APIClient)"""
        self.api_client.test_default_versions_api()

    def show_error(self, title, message):
        """Show error dialog"""
        messagebox.showerror(title, message)

    def show_info(self, title, message):
        """Show info dialog"""
        messagebox.showinfo(title, message)

    def get_basic_auth_password_from_keepass(self, target_entry=None, password_type="basic_auth"):
        """Get password from KeePass (delegates to KeePassHandler)"""
        self.keepass_handler.get_basic_auth_password_from_keepass(target_entry, password_type)
            
    
    def find_basic_auth_password_entry(self, folder_structure):
        """Find Basic Auth password entry in KeePass folder structure (delegates to KeePassHandler)"""
        return self.keepass_handler.find_basic_auth_password_entry(folder_structure)
    
    def find_webdav_admin_password_entry(self, folder_structure):
        """Find Webdav Admin password entry in KeePass folder structure (delegates to KeePassHandler)"""
        return self.keepass_handler.find_webdav_admin_password_entry(folder_structure)

    def find_folder_id_by_name(self, folder_structure, search_name):
        """Find folder ID by name (delegates to KeePassHandler)"""
        return self.keepass_handler.find_folder_id_by_name(folder_structure, search_name)

    def get_subfolders(self, folder_structure):
        """Get subfolders from folder structure (delegates to KeePassHandler)"""
        return self.keepass_handler.get_subfolders(folder_structure)

    def print_all_credentials(self, folder_structure, path=""):
        """Print all credentials in the folder structure for debugging (delegates to KeePassHandler)"""
        self.keepass_handler.print_all_credentials(folder_structure, path)

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget (delegates to create_tooltip from utils)"""
        return create_tooltip(widget, text, parent_window=self.root)

    def clear_keepass_credentials(self):
        """Clear stored KeePass credentials (delegates to KeePassHandler)"""
        self.keepass_handler.clear_keepass_credentials()

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

        # Update DetectionManager with new base directory from config
        if "file_detection_base_directory" in self.config_manager.config:
            self.detection_manager.set_base_directory(
                self.config_manager.config["file_detection_base_directory"]
            )

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
                "hostname_detection": {
                    "detect_environment": False
                }
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
                "hostname_detection": {
                    "detect_environment": False
                }
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


    def on_installer_overrides_changed(self):
        """Handler for when installer overrides checkbox is changed"""
        self.config_manager.config["installer_overrides_enabled"] = self.installer_overrides_var.get()
        self.config_manager.schedule_save()

    def on_override_properties_changed(self):
        """Handler for when override property checkboxes are changed"""
        self.config_manager.config["installer_overrides_properties"] = {
            "check-alive": self.override_check_alive_var.get(),
            "start-application": self.override_start_app_var.get(),
        }
        self.config_manager.schedule_save()

    def on_remove_overrides_changed(self):
        """Handler for when remove overrides after install checkbox is changed"""
        self.config_manager.config["remove_overrides_after_install"] = self.remove_overrides_var.get()
        self.config_manager.schedule_save()

    def open_overrides_settings(self):
        """Open dialog to configure per-component installer overrides"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Installer Override Settings")
        dialog.geometry("400x380")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.after(100, lambda: dialog.grab_set())

        # Header
        header = ctk.CTkLabel(dialog, text="Select components for installer overrides",
                              font=ctk.CTkFont(size=14, weight="bold"))
        header.pack(pady=(15, 5))

        desc = ctk.CTkLabel(dialog, text="Override files skip the health check (check-alive)\nduring component installation.",
                            font=ctk.CTkFont(size=12), text_color="gray")
        desc.pack(pady=(0, 10))

        # Get current per-component settings
        components = self.config_manager.config.get("installer_overrides_components", {})
        default_all = {
            "POS": True, "ONEX-POS": True, "WDM": True,
            "FLOW-SERVICE": True, "LPA-SERVICE": True,
            "STOREHUB-SERVICE": True, "RCS-SERVICE": True,
        }
        for k, v in default_all.items():
            components.setdefault(k, v)

        # Component display names
        display_names = {
            "POS": "POS",
            "ONEX-POS": "OneX POS",
            "WDM": "WDM",
            "FLOW-SERVICE": "Flow Service",
            "LPA-SERVICE": "LPA Service",
            "STOREHUB-SERVICE": "StoreHub Service",
            "RCS-SERVICE": "RCS Service",
        }

        # Create checkboxes
        comp_vars = {}
        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(padx=20, pady=5, fill="x")

        for comp_key in default_all:
            var = ctk.BooleanVar(value=components.get(comp_key, True))
            comp_vars[comp_key] = var
            cb = ctk.CTkCheckBox(frame, text=display_names[comp_key], variable=var)
            cb.pack(anchor="w", pady=3, padx=10)

        # Select All / Deselect All buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=5)

        def select_all():
            for v in comp_vars.values():
                v.set(True)

        def deselect_all():
            for v in comp_vars.values():
                v.set(False)

        ctk.CTkButton(btn_frame, text="Select All", width=100, command=select_all).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Deselect All", width=100, command=deselect_all).pack(side="left", padx=5)

        # Save / Cancel buttons
        action_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        action_frame.pack(pady=(10, 15))

        def save_and_close():
            result = {k: v.get() for k, v in comp_vars.items()}
            self.config_manager.config["installer_overrides_components"] = result
            self.config_manager.schedule_save()
            dialog.destroy()

        ctk.CTkButton(action_frame, text="Save", width=100, command=save_and_close).pack(side="left", padx=5)
        ctk.CTkButton(action_frame, text="Cancel", width=100, fg_color="gray",
                       command=dialog.destroy).pack(side="left", padx=5)

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