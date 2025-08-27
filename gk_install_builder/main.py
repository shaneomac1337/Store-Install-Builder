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
# Add parent directory to path to import PleasantPasswordClient
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pleasant_password_client import PleasantPasswordClient

def bind_mousewheel_to_frame(frame):
    """
    Bind mousewheel events to a frame to enable scrolling in Linux.
    
    Args:
        frame: The frame to add scrolling to (must be a CTkScrollableFrame)
    """
    # Skip if not a CTkScrollableFrame
    if not hasattr(frame, '_parent_canvas'):
        return
    
    # For Linux, we need special handling for Button-4 and Button-5 events
    if sys.platform.startswith('linux'):
        # Find the root window that contains this frame
        root = frame.winfo_toplevel()
        
        # Create a unique tag for this frame to avoid conflicts between windows
        frame_id = str(id(frame))
        scroll_tag = f"scroll_{frame_id}"
        
        # Function for scrolling up
        def _on_mousewheel_up(event):
            # Get the window under the cursor
            widget_under_cursor = event.widget.winfo_containing(event.x_root, event.y_root)
            
            # Check if the widget is in the same window hierarchy as our frame
            current_widget = widget_under_cursor
            while current_widget:
                if current_widget == frame or current_widget == frame._parent_canvas:
                    frame._parent_canvas.yview_scroll(-1, "units")
                    return "break"
                current_widget = current_widget.master
            
            # If we're not in the right window, don't handle the event
            return
        
        # Function for scrolling down
        def _on_mousewheel_down(event):
            # Get the window under the cursor
            widget_under_cursor = event.widget.winfo_containing(event.x_root, event.y_root)
            
            # Check if the widget is in the same window hierarchy as our frame
            current_widget = widget_under_cursor
            while current_widget:
                if current_widget == frame or current_widget == frame._parent_canvas:
                    frame._parent_canvas.yview_scroll(1, "units")
                    return "break"
                current_widget = current_widget.master
            
            # If we're not in the right window, don't handle the event
            return
        
        # Store event handlers
        if not hasattr(frame, '_scroll_handlers'):
            frame._scroll_handlers = {}
        frame._scroll_handlers[scroll_tag] = (_on_mousewheel_up, _on_mousewheel_down)
        
        # Bind to the toplevel window containing this frame, but not globally
        root.bind("<Button-4>", _on_mousewheel_up, add="+")
        root.bind("<Button-5>", _on_mousewheel_down, add="+")
        
        # Create cleanup function to remove bindings when window is destroyed
        def _cleanup_bindings():
            if hasattr(root, "bind"):  # Check if root still exists
                try:
                    root.unbind("<Button-4>", _on_mousewheel_up)
                    root.unbind("<Button-5>", _on_mousewheel_down)
                except:
                    pass
                
        # Bind cleanup to window destruction
        root.bind("<Destroy>", lambda e: _cleanup_bindings(), add="+")
    else:
        # Windows and macOS use MouseWheel event
        def _on_mousewheel(event):
            # Get the window under the cursor
            widget_under_cursor = event.widget.winfo_containing(event.x_root, event.y_root)
            
            # Check if the widget is in the same window hierarchy as our frame
            current_widget = widget_under_cursor
            while current_widget:
                if current_widget == frame or current_widget == frame._parent_canvas:
                    # Increase scrolling speed on Windows by using a larger multiplier
                    if sys.platform == 'win32':
                        # Changed from 20 to 5 for much faster scrolling on Windows
                        frame._parent_canvas.yview_scroll(int(-1*(event.delta/5)), "units")
                    else:
                        # Keep original behavior for other platforms
                        frame._parent_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                    return "break"
                current_widget = current_widget.master
            
            # If we're not in the right window, don't handle the event
            return
        
        # Store event handler
        frame_id = str(id(frame))
        scroll_tag = f"scroll_{frame_id}"
        if not hasattr(frame, '_scroll_handlers'):
            frame._scroll_handlers = {}
        frame._scroll_handlers[scroll_tag] = _on_mousewheel
        
        # Find the root window that contains this frame
        root = frame.winfo_toplevel()
        
        # Bind to the toplevel window
        root.bind("<MouseWheel>", _on_mousewheel, add="+")
        
        # Create cleanup function
        def _cleanup_bindings():
            if hasattr(root, "bind"):  # Check if root still exists
                try:
                    root.unbind("<MouseWheel>", _on_mousewheel)
                except:
                    pass
                
        # Bind cleanup to window destruction
        root.bind("<Destroy>", lambda e: _cleanup_bindings(), add="+")

class LauncherSettingsEditor:
    def __init__(self, parent, config_manager, project_generator):
        self.parent = parent
        self.config_manager = config_manager
        self.project_generator = project_generator
        self.window = None
        self.settings = {}
        
        # Translation dictionary for parameter names
        self.parameter_labels = {
            "applicationJmxPort": "Application JMX listen port",
            "updaterJmxPort": "Updater JMX listen port",
            "createShortcuts": "Create Desktop Shortcuts",
            "keepFiles": "Keep Installer Files",
            "applicationServerHttpPort": "Tomcat HTTP port",
            "applicationServerHttpsPort": "Tomcat HTTPS port",
            "applicationServerShutdownPort": "Tomcat Shutdown port",
            "applicationServerJmxPort": "Tomcat JMX listen port",
            "applicationJmsPort": "JMS Port",
            "firebirdServerPath": "Firebird Installation directory",
            "firebirdServerPort": "Firebird listen port",
            "firebirdServerUser": "Firebird DB Admin",
            "firebirdServerPassword": "Firebird DB Password"
        }
        
        # Tooltips for parameters
        self.parameter_tooltips = {
            "applicationJmxPort": "Port used for JMX monitoring of the main application",
            "updaterJmxPort": "Port used for JMX monitoring of the updater service",
            "createShortcuts": "Set to 1 to create desktop shortcuts, 0 to disable",
            "keepFiles": "Set to 1 to keep installer files after installation, 0 to delete them",
            "applicationServerHttpPort": "HTTP port for Tomcat server (default: 8080 for WDM, 8180 for services)",
            "applicationServerHttpsPort": "HTTPS port for Tomcat server (default: 8443 for WDM, 8543 for services)",
            "applicationServerShutdownPort": "Port used to shut down Tomcat server (default: 8005)",
            "applicationServerJmxPort": "Port used for JMX monitoring of Tomcat (default: 52222)",
            "applicationJmsPort": "Port used for JMS messaging (StoreHub only, default: 7000)",
            "firebirdServerPath": "Path to Firebird server installation (not 'localhost')",
            "firebirdServerPort": "Port used by Firebird database server (default: 3050)",
            "firebirdServerUser": "Username for Firebird database administrator (default: SYSDBA)",
            "firebirdServerPassword": "Password for Firebird database administrator (default: masterkey)"
        }
    
    def open_editor(self):
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()  # Force focus on Linux
            return
            
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("Launcher Settings Editor")
        self.window.geometry("800x600")
        
        # Add these lines to fix Linux visibility issue
        self.window.update_idletasks()
        self.window.update()
        
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Create main frame with scrollbar
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Force another update to ensure contents are displayed
        self.window.after(100, self.window.update_idletasks)
        self.window.after(100, self.window.update)
        
        # Create tabs for each component type
        tab_view = ctk.CTkTabview(main_frame)
        tab_view.pack(fill="both", expand=True, padx=10, pady=10)
        
        component_types = ["POS", "WDM", "FLOW-SERVICE", "LPA-SERVICE", "STOREHUB-SERVICE"]
        
        # Initialize settings dictionary
        self.settings = {}
        for component_type in component_types:
            self.settings[component_type] = {}
        
        # Load default settings
        self.load_default_settings()
        
        # Create tabs for each component
        for component_type in component_types:
            tab = tab_view.add(component_type)
            
            # Create a frame for this component's settings
            settings_frame = ctk.CTkFrame(tab)
            settings_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Add a label with instructions
            instructions = ctk.CTkLabel(
                settings_frame, 
                text=f"Edit the launcher settings for {component_type}. These settings will be used when generating the installation files.",
                wraplength=700
            )
            instructions.pack(pady=(0, 10), padx=10, anchor="w")
            
            # Create a scrollable frame for settings using CTkScrollableFrame
            scrollable_settings = ctk.CTkScrollableFrame(settings_frame)
            scrollable_settings.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Apply mousewheel binding for Linux scrolling
            bind_mousewheel_to_frame(scrollable_settings)
            
            # Create entries for each setting
            row = 0
            for key, value in self.settings[component_type].items():
                frame = ctk.CTkFrame(scrollable_settings, fg_color="transparent")
                frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
                frame.grid_columnconfigure(1, weight=1)
                
                # Use the translated label if available, otherwise use the original key
                display_label = self.parameter_labels.get(key, key)
                label = ctk.CTkLabel(frame, text=display_label, width=250, anchor="w")
                label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
                
                entry = ctk.CTkEntry(frame, width=400)
                entry.insert(0, value)
                entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
                
                # Add tooltip if available
                if key in self.parameter_tooltips:
                    self.create_tooltip(label, self.parameter_tooltips[key])
                    self.create_tooltip(entry, self.parameter_tooltips[key])
                
                # Store the entry widget in the settings dictionary
                self.settings[component_type][key] = {"value": value, "entry": entry}
                
                row += 1
        
        # Add buttons at the bottom
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        save_button = ctk.CTkButton(
            button_frame, 
            text="Save Settings", 
            command=self.save_settings
        )
        save_button.pack(side="right", padx=10)
        
        cancel_button = ctk.CTkButton(
            button_frame, 
            text="Cancel", 
            command=self.window.destroy
        )
        cancel_button.pack(side="right", padx=10)
        
        # Set default tab
        tab_view.set("WDM")
    
    def load_default_settings(self):
        """Load default settings for each component type"""
        # Get platform-specific defaults
        platform = self.config_manager.config.get("platform", "Windows")
        default_firebird_path = "C:\\Program Files\\Firebird\\Firebird_3_0" if platform == "Windows" else "/opt/firebird"
        firebird_path = self.config_manager.config.get("firebird_server_path", default_firebird_path)

        # POS settings
        self.settings["POS"] = {
            "applicationJmxPort": "3333",
            "updaterJmxPort": "4333",
            "createShortcuts": "0",
            "keepFiles": "0"
        }
        
        # WDM settings
        self.settings["WDM"] = {
            "applicationServerHttpPort": "8080",
            "applicationServerHttpsPort": "8443",
            "applicationServerShutdownPort": "8005",
            "applicationServerJmxPort": "52222",
            "updaterJmxPort": "4333",
            "keepFiles": "0"
        }
        
        # Flow Service settings
        self.settings["FLOW-SERVICE"] = {
            "applicationServerHttpPort": "8180",
            "applicationServerHttpsPort": "8543",
            "applicationServerShutdownPort": "8005",
            "applicationServerJmxPort": "52222",
            "updaterJmxPort": "4333",
            "keepFiles": "0"
        }
        
        # LPA Service settings
        self.settings["LPA-SERVICE"] = {
            "applicationServerHttpPort": "8180",
            "applicationServerHttpsPort": "8543",
            "applicationServerShutdownPort": "8005",
            "applicationServerJmxPort": "52222",
            "updaterJmxPort": "4333",
            "keepFiles": "0"
        }
        
        # StoreHub Service settings
        self.settings["STOREHUB-SERVICE"] = {
            "applicationServerHttpPort": "8180",
            "applicationServerHttpsPort": "8543",
            "applicationServerShutdownPort": "8005",
            "applicationServerJmxPort": "52222",
            "applicationJmsPort": "7001",
            "updaterJmxPort": "4333",
            "firebirdServerPath": firebird_path,
            "firebirdServerPort": "3050",
            "firebirdServerUser": "SYSDBA",
            "firebirdServerPassword": "masterkey",
            "keepFiles": "0"
        }
        
        # Try to load existing templates from the output directory
        self._load_existing_templates()
        
        # Load settings from config if available
        for component_type in self.settings:
            config_key = f"{component_type.lower().replace('-', '_')}_launcher_settings"
            if config_key in self.config_manager.config:
                saved_settings = self.config_manager.config[config_key]
                print(f"Loading {config_key} settings from config: {saved_settings}")
                for key in self.settings[component_type].keys():
                    if key in saved_settings:
                        self.settings[component_type][key] = saved_settings[key]
    
    def _load_existing_templates(self):
        """Load settings from existing templates in the output directory"""
        # Get the output directory from the config
        output_dir = self.config_manager.config.get("output_dir", "")
        if not output_dir:
            return
            
        # Check if the output directory exists
        launchers_dir = os.path.join(output_dir, "helper", "launchers")
        if not os.path.exists(launchers_dir):
            return
            
        # Load settings from existing templates
        template_files = {
            "POS": "launcher.pos.template",
            "WDM": "launcher.wdm.template",
            "FLOW-SERVICE": "launcher.flow-service.template",
            "LPA-SERVICE": "launcher.lpa-service.template",
            "STOREHUB-SERVICE": "launcher.storehub-service.template"
        }
        
        for component_type, filename in template_files.items():
            file_path = os.path.join(launchers_dir, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        
                    # Parse the template content
                    for line in content.strip().split('\n'):
                        if line.startswith('#') or not line.strip():
                            continue
                        
                        if '=' in line:
                            key, value = line.split('=', 1)
                            
                            # Skip placeholder values
                            if '@' in value:
                                continue
                            
                            # Add the key-value pair to the settings
                            if key not in self.settings[component_type]:
                                self.settings[component_type][key] = value
                                
                    print(f"Loaded settings from existing template: {filename}")
                except Exception as e:
                    print(f"Error loading settings from template {filename}: {str(e)}")
    
    def save_settings(self):
        """Save settings to config and close the window"""
        # Update settings from entries
        for component_type in self.settings:
            component_settings = {}
            for key, item in self.settings[component_type].items():
                if isinstance(item, dict) and "entry" in item:
                    component_settings[key] = item["entry"].get()
                else:
                    component_settings[key] = item
            
            # Save to config with the correct key format
            config_key = f"{component_type.lower().replace('-', '_')}_launcher_settings"
            self.config_manager.config[config_key] = component_settings
            
            # Print debug info
            print(f"Saving {config_key} settings:")
            for k, v in component_settings.items():
                print(f"  {k}: {v}")
        
        # Save config
        self.config_manager.save_config()
        
        # Force regeneration of launcher templates if output directory exists
        output_dir = self.config_manager.config.get("output_dir", "")
        if output_dir and os.path.exists(output_dir):
            launchers_dir = os.path.join(output_dir, "helper", "launchers")
            os.makedirs(launchers_dir, exist_ok=True)
            
            try:
                # Generate launcher templates with custom settings
                self.project_generator._generate_launcher_templates(launchers_dir, self.config_manager.config)
                messagebox.showinfo("Success", "Launcher settings saved and templates updated successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update launcher templates: {str(e)}")
                return
        else:
            messagebox.showinfo("Success", "Launcher settings saved successfully!")
        
        self.window.destroy()
    
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        tooltip_window = None
        
        def show_tooltip(x, y):
            nonlocal tooltip_window
            tooltip_window = ctk.CTkToplevel(self.window)
            tooltip_window.wm_overrideredirect(True)  # Remove window decorations
            tooltip_window.wm_geometry(f"+{x+15}+{y+10}")
            tooltip_window.attributes("-topmost", True)
            
            # Create a frame with a border
            frame = ctk.CTkFrame(tooltip_window, border_width=1)
            frame.pack(fill="both", expand=True)
            
            # Add the tooltip text
            label = ctk.CTkLabel(
                frame,
                text=text,
                wraplength=300,
                justify="left",
                padx=5,
                pady=5
            )
            label.pack()
            
            # Ensure the tooltip is shown
            tooltip_window.update_idletasks()
            tooltip_window.deiconify()
        
        def enter(event):
            x, y = event.x_root, event.y_root
            # Schedule showing the tooltip after a delay
            widget._tooltip_after_id = widget.after(500, lambda: show_tooltip(x, y))
        
        def leave(event):
            # Cancel showing the tooltip if it hasn't been shown yet
            if hasattr(widget, '_tooltip_after_id'):
                try:
                    widget.after_cancel(widget._tooltip_after_id)
                    widget._tooltip_after_id = None
                except ValueError:
                    # The after_id was already cancelled or is invalid
                    pass
            
            # Destroy the tooltip window if it exists
            nonlocal tooltip_window
            if tooltip_window is not None:
                try:
                    tooltip_window.destroy()
                    tooltip_window = None
                except:
                    pass
        
        # Bind events to show/hide the tooltip
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
        widget.bind("<Motion>", lambda e: leave(e) or enter(e))
        
        # Also bind to window close to ensure tooltips are cleaned up
        # Use a safer approach that doesn't trigger errors
        def safe_leave(event):
            try:
                leave(event)
            except:
                pass
                
        self.window.bind("<Destroy>", safe_leave, add="+")

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
            text="v5.25",
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
        """Auto-fill fields based on the base URL"""
        # Skip if URL is empty
        if not base_url:
            return
        
        print(f"Auto-filling based on URL: {base_url}")
        
        # Get current platform
        platform = self.platform_var.get() if hasattr(self, 'platform_var') else "Windows"
        
        # Determine default installation directory based on platform
        default_install_dir = "/usr/local/gkretail" if platform == "Linux" else "C:\\gkretail"
        
        # Extract project name from URL as the part after the first dot
        extracted_project_name = ""
        project_code = ""
        if "." in base_url:
            parts = base_url.split(".")
            if len(parts) > 1:
                # Extract the part after the first dot (index 1) and uppercase it for project code
                project_code = parts[1].upper()
                # Use this for prefix detection in system types
                print(f"Detected project code from URL: {project_code}")
                
                # Also use it as the project name if not set
                extracted_project_name = project_code
        
        # Auto-fill system types based on the detected project code
        if project_code:
            # Use the detected project code for system types
            pos_system_type = f"{project_code}-OPOS-CLOUD"
            wdm_system_type = f"{project_code}-wdm"
            # FLOWSERVICE always uses GKR prefix (exception)
            flow_service_system_type = "GKR-FLOWSERVICE-CLOUD"
            lpa_service_system_type = f"{project_code}-lps-lpa"
            storehub_service_system_type = f"{project_code}-sh-cloud"
            
            print(f"Setting system types based on detected project code: {project_code}")
        else:
            # Default to CSE system types if no project code detected
            pos_system_type = "CSE-OPOS-CLOUD"
            wdm_system_type = "CSE-wdm"
            flow_service_system_type = "GKR-FLOWSERVICE-CLOUD"
            lpa_service_system_type = "CSE-lps-lpa"
            storehub_service_system_type = "CSE-sh-cloud"
        
        # Update project name entry if it's empty and we extracted a valid name
        if extracted_project_name and self.config_manager.get_entry("project_name") and not self.config_manager.get_entry("project_name").get():
            self.config_manager.update_entry_value("project_name", extracted_project_name)
            print(f"Auto-filled project name: {extracted_project_name}")
        
        # Get current project name (either from entry or use the extracted name as fallback)
        project_name = self.config_manager.get_entry("project_name").get() if self.config_manager.get_entry("project_name") else extracted_project_name
        
        # Create a structured output directory using the original pattern: ProjectName/base_url
        if self.config_manager.get_entry("output_dir"):
            if project_name:
                # Use the project name and full URL to create the directory structure
                output_dir = os.path.join(project_name, base_url)
            else:
                # Fallback to a simple directory if project name is missing
                output_dir = "generated_scripts"
                
            self.config_manager.update_entry_value("output_dir", output_dir)
            print(f"Auto-filled output directory: {output_dir}")
        
        # Auto-fill certificate path
        if self.config_manager.get_entry("certificate_path"):
            # Use a certificate path inside the output directory
            if project_name:
                cert_path = os.path.join(project_name, base_url, "certificate.p12")
            else:
                # Fallback if project name is not set
                cert_path = f"generated_scripts/{base_url}_certificate.p12"
            
            self.config_manager.update_entry_value("certificate_path", cert_path)
            print(f"Auto-filled certificate path: {cert_path}")
        
        # Update system types
        if self.config_manager.get_entry("pos_system_type"):
            self.config_manager.update_entry_value("pos_system_type", pos_system_type)
            print(f"Auto-filled POS system type: {pos_system_type}")
        
        if self.config_manager.get_entry("wdm_system_type"):
            self.config_manager.update_entry_value("wdm_system_type", wdm_system_type)
            print(f"Auto-filled WDM system type: {wdm_system_type}")
        
        if self.config_manager.get_entry("flow_service_system_type"):
            self.config_manager.update_entry_value("flow_service_system_type", flow_service_system_type)
            print(f"Auto-filled Flow Service system type: {flow_service_system_type}")
        
        if self.config_manager.get_entry("lpa_service_system_type"):
            self.config_manager.update_entry_value("lpa_service_system_type", lpa_service_system_type)
            print(f"Auto-filled LPA Service system type: {lpa_service_system_type}")
        
        if self.config_manager.get_entry("storehub_service_system_type"):
            self.config_manager.update_entry_value("storehub_service_system_type", storehub_service_system_type)
            print(f"Auto-filled StoreHub Service system type: {storehub_service_system_type}")
        
        # Set the base install directory only if other values were updated
        base_dir_entry = self.config_manager.get_entry("base_install_dir")
        current = base_dir_entry.get() if base_dir_entry else self.config_manager.config.get("base_install_dir", "")
        if not current or (platform == "Windows" and "/" in current) or (platform == "Linux" and "\\" in current):
            if base_dir_entry:
                base_dir_entry.delete(0, 'end')
                base_dir_entry.insert(0, default_install_dir)
            self.config_manager.config["base_install_dir"] = default_install_dir
            print(f"Auto-filled base install directory: {default_install_dir}")
        # Only set these other defaults if their fields are empty
        if self.config_manager.get_entry("username") and not self.config_manager.get_entry("username").get():
            self.config_manager.update_entry_value("username", "launchpad")
        if self.config_manager.get_entry("eh_launchpad_username") and not self.config_manager.get_entry("eh_launchpad_username").get():
            self.config_manager.update_entry_value("eh_launchpad_username", "1001")
        if self.config_manager.get_entry("ssl_password") and not self.config_manager.get_entry("ssl_password").get():
            self.config_manager.update_entry_value("ssl_password", "changeit")
    
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
            text="Use Default Versions (fetch from Employee Hub Function Pack)",
            variable=self.use_default_versions_var,
            command=self.toggle_default_versions
        )
        default_versions_checkbox.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.create_tooltip(default_versions_checkbox, "When enabled, the installation script will fetch component versions from the Employee Hub Function Pack API instead of using hardcoded versions")

        # Test API button next to the checkbox
        test_api_button = ctk.CTkButton(
            grid_frame,
            text="Test API",
            command=self.test_default_versions_api,
            width=80,
            height=28
        )
        test_api_button.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.create_tooltip(test_api_button, "Test the Employee Hub Function Pack API to verify it can fetch default component versions")
        
        # Get project version from config
        project_version = self.config_manager.config.get("version", "")
        
        # Store version field references for show/hide functionality
        self.version_fields = []

        # POS Version
        pos_label = ctk.CTkLabel(grid_frame, text="POS Version:")
        pos_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.pos_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.pos_version_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.pos_version_entry.insert(0, self.config_manager.config.get("pos_version", project_version))
        self.config_manager.register_entry("pos_version", self.pos_version_entry)
        self.create_tooltip(pos_label, "Version for POS components (applies to all POS system types)")
        self.create_tooltip(self.pos_version_entry, "Example: v1.0.0")
        self.version_fields.extend([pos_label, self.pos_version_entry])

        # WDM Version
        wdm_label = ctk.CTkLabel(grid_frame, text="WDM Version:")
        wdm_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.wdm_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.wdm_version_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        self.wdm_version_entry.insert(0, self.config_manager.config.get("wdm_version", project_version))
        self.config_manager.register_entry("wdm_version", self.wdm_version_entry)
        self.create_tooltip(wdm_label, "Version for WDM components (applies to all WDM system types)")
        self.create_tooltip(self.wdm_version_entry, "Example: v1.0.0")
        self.version_fields.extend([wdm_label, self.wdm_version_entry])

        # Flow Service Version
        flow_service_label = ctk.CTkLabel(grid_frame, text="Flow Service Version:")
        flow_service_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.flow_service_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.flow_service_version_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.flow_service_version_entry.insert(0, self.config_manager.config.get("flow_service_version", project_version))
        self.config_manager.register_entry("flow_service_version", self.flow_service_version_entry)
        self.create_tooltip(flow_service_label, "Version for Flow Service components")
        self.create_tooltip(self.flow_service_version_entry, "Example: v1.0.0")
        self.version_fields.extend([flow_service_label, self.flow_service_version_entry])

        # LPA Service Version
        lpa_service_label = ctk.CTkLabel(grid_frame, text="LPA Service Version:")
        lpa_service_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.lpa_service_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.lpa_service_version_entry.grid(row=5, column=1, padx=10, pady=5, sticky="w")
        self.lpa_service_version_entry.insert(0, self.config_manager.config.get("lpa_service_version", project_version))
        self.config_manager.register_entry("lpa_service_version", self.lpa_service_version_entry)
        self.create_tooltip(lpa_service_label, "Version for LPA Service components")
        self.create_tooltip(self.lpa_service_version_entry, "Example: v1.0.0")
        self.version_fields.extend([lpa_service_label, self.lpa_service_version_entry])

        # StoreHub Service Version
        storehub_service_label = ctk.CTkLabel(grid_frame, text="StoreHub Service Version:")
        storehub_service_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.storehub_service_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.storehub_service_version_entry.grid(row=6, column=1, padx=10, pady=5, sticky="w")
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
            print("Default versions enabled: Installation script will fetch component versions from Employee Hub Function Pack API")
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
        """Test the Employee Hub Function Pack API to fetch default versions"""
        try:
            # Force save current GUI values to config before testing
            print("Forcing config update from GUI fields...")
            self.config_manager.update_config_from_entries()
            self.config_manager.save_config_silent()

            # Get base URL from config
            base_url = self.config_manager.config.get("base_url", "")
            if not base_url:
                messagebox.showerror("Error", "Please configure the Base URL first")
                return

            # Show loading message
            loading_dialog = ctk.CTkToplevel(self.root)
            loading_dialog.title("Testing API")
            loading_dialog.geometry("400x250")
            loading_dialog.transient(self.root)

            # Center the dialog
            loading_dialog.update_idletasks()
            x = (loading_dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (loading_dialog.winfo_screenheight() // 2) - (250 // 2)
            loading_dialog.geometry(f"400x250+{x}+{y}")

            loading_label = ctk.CTkLabel(loading_dialog, text="Testing Employee Hub Function Pack API...\nGenerating authentication token...\nPlease wait...")
            loading_label.pack(expand=True)

            # Update the dialog and ensure it's visible before grabbing
            loading_dialog.update()
            loading_dialog.deiconify()  # Ensure window is visible

            # Try to grab focus with error handling for Linux compatibility
            try:
                loading_dialog.grab_set()
            except Exception as e:
                print(f"Warning: Could not grab window focus: {e}")
                # Continue without grab - dialog will still work

            # Try to generate token using credentials from config
            bearer_token = self._generate_api_token(base_url, loading_label, loading_dialog)

            if not bearer_token:
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

            # Initialize versions tracking
            versions = {
                "POS": {"value": None, "source": None},
                "WDM": {"value": None, "source": None},
                "FLOW-SERVICE": {"value": None, "source": None},
                "LPA-SERVICE": {"value": None, "source": None},
                "STOREHUB-SERVICE": {"value": None, "source": None}
            }

            # Step 1: Try FP scope first (modified/customized versions)
            fp_api_url = f"https://{base_url}/employee-hub-service/services/rest/v1/properties?scope=FP&referenceId=platform"

            try:
                fp_response = requests.get(fp_api_url, headers=headers, timeout=30, verify=False)
                if fp_response.status_code == 200:
                    fp_data = fp_response.json()

                    # Parse FP scope results
                    for property_item in fp_data:
                        prop_id = property_item.get("propertyId", "")
                        value = property_item.get("value", "")

                        if prop_id == "POSClient_Version" and value:
                            versions["POS"] = {"value": value, "source": "FP (Modified)"}
                        elif prop_id == "WDM_Version" and value:
                            versions["WDM"] = {"value": value, "source": "FP (Modified)"}
                        elif prop_id == "FlowService_Version" and value:
                            versions["FLOW-SERVICE"] = {"value": value, "source": "FP (Modified)"}
                        elif prop_id == "LPA_Version" and value:
                            versions["LPA-SERVICE"] = {"value": value, "source": "FP (Modified)"}
                        elif prop_id == "StoreHub_Version" and value:
                            versions["STOREHUB-SERVICE"] = {"value": value, "source": "FP (Modified)"}
            except Exception as e:
                print(f"Warning: FP scope request failed: {e}")

            # Step 2: For components not found in FP, try FPD scope (default versions)
            missing_components = [comp for comp, data in versions.items() if data["value"] is None]

            if missing_components:
                loading_label.configure(text="Testing Employee Hub Function Pack API...\nFetching missing components (FPD scope)...\nPlease wait...")
                loading_dialog.update()

                fpd_api_url = f"https://{base_url}/employee-hub-service/services/rest/v1/properties?scope=FPD&referenceId=platform"

                try:
                    fpd_response = requests.get(fpd_api_url, headers=headers, timeout=30, verify=False)
                    if fpd_response.status_code == 200:
                        fpd_data = fpd_response.json()

                        # Parse FPD scope results for missing components only
                        for property_item in fpd_data:
                            prop_id = property_item.get("propertyId", "")
                            value = property_item.get("value", "")

                            if prop_id == "POSClient_Version" and value and versions["POS"]["value"] is None:
                                versions["POS"] = {"value": value, "source": "FPD (Default)"}
                            elif prop_id == "WDM_Version" and value and versions["WDM"]["value"] is None:
                                versions["WDM"] = {"value": value, "source": "FPD (Default)"}
                            elif prop_id == "FlowService_Version" and value and versions["FLOW-SERVICE"]["value"] is None:
                                versions["FLOW-SERVICE"] = {"value": value, "source": "FPD (Default)"}
                            elif prop_id == "LPA_Version" and value and versions["LPA-SERVICE"]["value"] is None:
                                versions["LPA-SERVICE"] = {"value": value, "source": "FPD (Default)"}
                            elif prop_id == "StoreHub_Version" and value and versions["STOREHUB-SERVICE"]["value"] is None:
                                versions["STOREHUB-SERVICE"] = {"value": value, "source": "FPD (Default)"}
                except Exception as e:
                    print(f"Warning: FPD scope request failed: {e}")

            loading_dialog.destroy()

            # Show results with status and source for each component
            result_text = "✅ API Test Successful!\n\nComponent Version Status:\n\n"

            found_count = 0
            for component, data in versions.items():
                if data["value"]:
                    result_text += f"✅ {component}: {data['value']} ({data['source']})\n"
                    found_count += 1
                else:
                    result_text += f"❌ {component}: Not Found\n"

            result_text += f"\n📊 Summary: {found_count}/5 components found"
            result_text += f"\n🔍 Search Strategy: FP scope first, FPD scope for missing components"

            if found_count == 0:
                result_text += "\n\n⚠️ No component versions found in either FP or FPD scope"

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
            basic_auth_password = self.config_manager.config.get("launchpad_oauth2", "")
            form_password = self.config_manager.config.get("eh_launchpad_password", "")

            if not basic_auth_password or not form_password:
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
                'username': '1001',
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

            # Update loading message
            loading_label.configure(text="Requesting OAuth token...\nPlease wait...")
            loading_dialog.update()

            # Disable SSL warnings for this request
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            response = requests.post(token_url, headers=headers, data=form_data, timeout=30, verify=False)

            if response.status_code == 200:
                try:
                    token_data = response.json()
                    access_token = token_data.get('access_token')
                    if access_token:
                        return access_token
                except Exception:
                    pass

            return None

        except Exception:
            return None

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
        """Display author information in a dialog"""
        # Create a new toplevel window
        author_window = ctk.CTkToplevel(self.root)
        author_window.title("About")
        # Make the window taller to fit all content including copyright
        author_window.geometry("400x750")
        
        # Add these lines to fix Linux visibility issue
        author_window.update_idletasks()
        author_window.update()
        
        author_window.transient(self.root)
        
        # Try-except block to handle potential grab_set issues on Linux
        try:
            author_window.grab_set()
        except Exception as e:
            print(f"Warning: Could not set grab on About window: {str(e)}")
            
        author_window.resizable(False, False)
        
        # Ensure the window appears on top
        author_window.focus_force()
        
        # Main content frame
        content_frame = ctk.CTkScrollableFrame(author_window)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Apply mousewheel binding for Linux scrolling
        bind_mousewheel_to_frame(content_frame)
        
        # Force another update to ensure contents are displayed
        author_window.after(100, author_window.update_idletasks)
        author_window.after(100, author_window.update)
        
        # Logo frame with more padding at the top
        logo_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        logo_frame.pack(pady=(15, 5))  # Reduced top padding to make more room below
        
        # Check if logo file exists and use it
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "gk_logo.png")
        
        if os.path.exists(logo_path):
            try:
                # Load the image using PIL/Pillow
                from PIL import Image
                original_image = Image.open(logo_path)
                
                # Get original dimensions to calculate proper aspect ratio
                orig_width, orig_height = original_image.size
                
                # Set a fixed width and calculate height based on aspect ratio
                display_width = 140
                display_height = int((display_width / orig_width) * orig_height)
                
                # Create the image with proper aspect ratio
                logo_image = ctk.CTkImage(
                    light_image=original_image,
                    dark_image=original_image,
                    size=(display_width, display_height)  # Size that preserves aspect ratio
                )
                
                logo_label = ctk.CTkLabel(
                    logo_frame,
                    image=logo_image,
                    text=""
                )
                logo_label.pack()
                
            except Exception as e:
                print(f"Error loading logo: {str(e)}")
                self._create_fallback_logo(logo_frame)
        else:
            self._create_fallback_logo(logo_frame)
        
        # App title
        title_label = ctk.CTkLabel(
            content_frame,
            text="Store Install Builder",
            font=("Helvetica", 18, "bold")
        )
        title_label.pack(pady=(5, 0))
        
        # Version
        version_label = ctk.CTkLabel(
            content_frame,
            text="Version 5.25",
            font=("Helvetica", 12),
            text_color=("gray50", "gray70")
        )
        version_label.pack(pady=(0, 5))
        
        # Copyright information - Moving these up in the layout, before technical info
        copyright_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        copyright_frame.pack(fill="x", padx=5, pady=0)
        
        copyright_label = ctk.CTkLabel(
            copyright_frame,
            text="© Created in 2025 by Martin Pěnkava",
            font=("Helvetica", 12),
            text_color=("gray50", "gray70")
        )
        copyright_label.pack(pady=5)
        
        # Contact info - Moving up with copyright
        contact_label = ctk.CTkLabel(
            copyright_frame,
            text="Contact: mpenkava@gk-software.com",
            font=("Helvetica", 12),
            text_color=("#3a7ebf", "#2b5f8f"),  # Blue text
            cursor="hand2"  # Hand cursor
        )
        contact_label.pack(pady=2)
        
        # Description
        description_label = ctk.CTkLabel(
            content_frame,
            text="GK Automation tool for creating installation packages for retail systems.",
            font=("Helvetica", 12),
            wraplength=350,
            justify="center"
        )
        description_label.pack(pady=(5, 15))
        
        # Divider
        divider = ctk.CTkFrame(content_frame, height=1, fg_color=("gray70", "gray30"))
        divider.pack(fill="x", padx=20, pady=5)
        
        # Technical info frame
        info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        info_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Technical info header
        tech_title = ctk.CTkLabel(
            info_frame,
            text="Technical Information",
            font=("Helvetica", 14, "bold"),
            justify="left"
        )
        tech_title.pack(anchor="w", padx=10, pady=(5, 10))
        
        # Get system information
        import platform as pf
        import customtkinter as ctk_info
        import sys
        
        # Simple function to add info rows
        def add_info_row(label, value):
            frame = ctk.CTkFrame(info_frame, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=5)
            
            label_widget = ctk.CTkLabel(
                frame,
                text=f"{label}:",
                font=("Helvetica", 12, "bold"),
                width=120,
                anchor="w"
            )
            label_widget.pack(side="left")
            
            value_widget = ctk.CTkLabel(
                frame,
                text=value,
                font=("Helvetica", 12),
                anchor="w",
                wraplength=220  # Fixed reasonable wraplength
            )
            value_widget.pack(side="left")
        
        # Add technical information with increased spacing
        add_info_row("Platform", pf.system())
        add_info_row("Python", sys.version.split()[0])
        add_info_row("CustomTkinter", ctk_info.__version__)
        
        # Components with longer text needs more space
        components_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        components_frame.pack(fill="x", padx=10, pady=5)
        
        components_label = ctk.CTkLabel(
            components_frame,
            text="Supports:",
            font=("Helvetica", 12, "bold"),
            width=120,
            anchor="w"
        )
        components_label.pack(side="left", anchor="n")
        
        components_value = ctk.CTkLabel(
            components_frame,
            text="POS, WDM, Flow Service,\nLPA, StoreHub",
            font=("Helvetica", 12),
            justify="left",
            anchor="w"
        )
        components_value.pack(side="left", anchor="n")
        
        # Divider
        divider2 = ctk.CTkFrame(info_frame, height=1, fg_color=("gray70", "gray30"))
        divider2.pack(fill="x", padx=20, pady=10)
        
        # Extra space before copyright
        spacer = ctk.CTkFrame(info_frame, fg_color="transparent", height=10)
        spacer.pack()
        
        # Author information
        author_label = ctk.CTkLabel(
            info_frame,
            text="Author: Martin Pěnkava",
            font=("Helvetica", 12, "bold"),
            justify="center"
        )
        author_label.pack(pady=(5, 5))
        
        # Close button
        close_button = ctk.CTkButton(
            content_frame,
            text="Close",
            command=author_window.destroy,
            width=100
        )
        close_button.pack(pady=10)
    
    def _create_fallback_logo(self, parent_frame):
        """Create a fallback text-based logo button"""
        logo_button = ctk.CTkButton(
            parent_frame,
            text="GK",  # Placeholder for logo
            font=("Helvetica", 28, "bold"),
            width=60,
            height=60,
            corner_radius=30,  # Circular button
            fg_color=("#3a7ebf", "#2b5f8f"),  # Blue background with dark variant
            hover_color=("#2b5f8f", "#1a4060"),  # Darker blue on hover
            text_color="white",  # White text
            command=None  # No action
        )
        logo_button.pack()
    
    def update_keepass_button(self):
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
            
            # Release window grab and destroy
            try:
                self.root.grab_release()
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
        # If no target entry is specified, use the appropriate password entry based on type
        if target_entry is None:
            if password_type == "basic_auth":
                target_entry = self.basic_auth_password_entry
            elif password_type == "webdav_admin":
                target_entry = self.webdav_admin_password_entry
            
        # Create a toplevel window
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("KeePass Authentication")
        dialog.geometry("500x550")  # Increased from 450x400
        dialog.transient(self.root)
        
        # Make sure the dialog is visible before setting grab
        dialog.update_idletasks()
        dialog.deiconify()
        dialog.wait_visibility()
        dialog.lift()
        dialog.focus_force()
        
        # Center the dialog on the parent window
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (500 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (550 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Now that the window is visible, set grab
        dialog.grab_set()
        
        # Add window close protocol handler
        def on_dialog_close():
            try:
                # Clean up any references
                if hasattr(dialog, 'client'):
                    delattr(dialog, 'client')
                if hasattr(dialog, 'folder_contents'):
                    delattr(dialog, 'folder_contents')
            except Exception:
                # Ignore any errors during cleanup
                pass
            finally:
                # Always destroy the dialog
                dialog.destroy()
            
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        # Username frame
        username_frame = ctk.CTkFrame(dialog)
        username_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkLabel(username_frame, text="Username:", width=100).pack(side="left")
        username_var = ctk.StringVar()
        username_entry = ctk.CTkEntry(username_frame, width=200, textvariable=username_var)
        username_entry.pack(side="left", padx=5)
        
        # If we have saved credentials, pre-fill the username
        if GKInstallBuilder.keepass_username:
            username_var.set(GKInstallBuilder.keepass_username)
        
        # Password frame
        password_frame = ctk.CTkFrame(dialog)
        password_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkLabel(password_frame, text="Password:", width=100).pack(side="left")
        password_var = ctk.StringVar()
        password_entry = ctk.CTkEntry(password_frame, width=200, textvariable=password_var, show="*")
        password_entry.pack(side="left", padx=5)
        
        # If we have saved credentials, pre-fill the password
        if GKInstallBuilder.keepass_password:
            password_var.set(GKInstallBuilder.keepass_password)
        
        # Remember credentials checkbox
        remember_var = ctk.BooleanVar(value=True)
        remember_checkbox = ctk.CTkCheckBox(
            dialog, 
            text="Remember credentials for this session", 
            variable=remember_var
        )
        remember_checkbox.pack(pady=5, padx=20, anchor="w")
        
        # Clear credentials button
        if GKInstallBuilder.keepass_client:
            clear_btn = ctk.CTkButton(
                dialog,
                text="Clear Saved Credentials",
                command=lambda: [
                    self.clear_keepass_credentials(), 
                    self.update_keepass_button(),
                    on_dialog_close()
                ]
            )
            clear_btn.pack(pady=5, padx=20)
        
        # Environment selection frame
        env_frame = ctk.CTkFrame(dialog)
        env_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkLabel(env_frame, text="Environment:", width=100).pack(side="left")
        env_var = ctk.StringVar(value="TEST")
        env_combo = ctk.CTkComboBox(env_frame, width=200, variable=env_var, values=["TEST", "PROD"], state="disabled")
        env_combo.pack(side="left", padx=5)
        
        # Connect button frame
        connect_frame = ctk.CTkFrame(dialog)
        connect_frame.pack(pady=10, fill="x", padx=20)
        
        connect_btn = ctk.CTkButton(
            connect_frame,
            text="Connect",
            command=lambda: connect_to_keepass()
        )
        connect_btn.pack(side="left", padx=10)
        
        # Status label
        status_var = ctk.StringVar(value="Not connected")
        status_label = ctk.CTkLabel(connect_frame, textvariable=status_var)
        status_label.pack(side="left", padx=10)
        
        # Detect Projects button (initially disabled)
        detect_projects_btn = ctk.CTkButton(
            dialog,
            text="Detect Projects",
            command=lambda: detect_projects(),
            state="disabled"
        )
        detect_projects_btn.pack(pady=5)
        
        # Get password button (initially disabled)
        get_password_btn = ctk.CTkButton(
            dialog,
            text="Get Password",
            command=lambda: get_password(),
            state="disabled"
        )
        get_password_btn.pack(pady=5)
        
        # Function to connect to KeePass
        def connect_to_keepass():
            try:
                status_var.set("Connecting to KeePass server...")
                dialog.update_idletasks()  # Force UI update
                
                # Validate inputs
                if not username_var.get().strip():
                    status_var.set("Error: Username cannot be empty")
                    return
                
                if not password_var.get().strip():
                    status_var.set("Error: Password cannot be empty")
                    return
                
                # Create a new client
                status_var.set("Authenticating with KeePass server...")
                dialog.update_idletasks()  # Force UI update
                
                client = PleasantPasswordClient(
                    base_url="https://keeserver.gk.gk-software.com/api/v5/rest/",
                    username=username_var.get(),
                    password=password_var.get()
                )
                
                status_var.set("Authentication successful! Saving settings...")
                dialog.update_idletasks()  # Force UI update
                
                # If remember checkbox is checked, save the credentials
                if remember_var.get():
                    GKInstallBuilder.keepass_client = client
                    GKInstallBuilder.keepass_username = username_var.get()
                    GKInstallBuilder.keepass_password = password_var.get()
                    
                    # Update the KeePass button state in the main window
                    self.update_keepass_button()
                
                # Store client for later use
                dialog.client = client
                
                # Update status and auto-detect environment
                status_var.set("Connected to KeePass! Auto-detecting environment...")
                dialog.update_idletasks()  # Force UI update
                
                # Run auto-detection immediately
                connect()
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400:
                    # Check for 2FA requirement
                    if 'X-Pleasant-OTP' in e.response.headers and e.response.headers['X-Pleasant-OTP'] == 'required':
                        otp_provider = e.response.headers.get('X-Pleasant-OTP-Provider', 'unknown')
                        status_var.set(f"Error: Two-factor authentication required ({otp_provider})")
                    else:
                        # Most likely invalid credentials
                        status_var.set("Error: Invalid username or password")
                elif e.response.status_code == 401:
                    status_var.set("Error: Unauthorized. Please check your credentials")
                elif e.response.status_code == 403:
                    status_var.set("Error: Access forbidden. You don't have permission to access this resource")
                elif e.response.status_code == 404:
                    status_var.set("Error: KeePass server endpoint not found")
                elif e.response.status_code >= 500:
                    status_var.set(f"Error: KeePass server error (HTTP {e.response.status_code})")
                else:
                    status_var.set(f"Error: HTTP error {e.response.status_code}")
            except requests.exceptions.ConnectionError:
                status_var.set("Error: Cannot connect to KeePass server. Check your network connection")
            except requests.exceptions.Timeout:
                status_var.set("Error: Connection to KeePass server timed out")
            except requests.exceptions.RequestException as e:
                status_var.set(f"Error: Request to KeePass server failed: {str(e)}")
            except json.JSONDecodeError:
                status_var.set("Error: Invalid response from KeePass server")
            except Exception as e:
                error_type = type(e).__name__
                status_var.set(f"Error: {error_type} - {str(e)}")
                print(f"Detailed error: {e}")
                import traceback
                traceback.print_exc()
        
        # Function to detect available projects
        def detect_projects():
            try:
                client = dialog.client
                
                status_var.set("Retrieving project list from KeePass... Please wait")
                dialog.update_idletasks()  # Force UI update
                
                # Get project folder
                projects_folder_id = "87300a24-9741-4d24-8a5c-a8b04e0b7049"
                folder_structure = client.get_folder(projects_folder_id)
                
                status_var.set("Processing project folders...")
                dialog.update_idletasks()  # Force UI update
                
                # Get all project folders
                projects = self.get_subfolders(folder_structure)
                
                if not projects:
                    status_var.set("No projects found!")
                    return
                    
                status_var.set(f"Found {len(projects)} projects. Preparing project list...")
                dialog.update_idletasks()  # Force UI update
                
                # Create a project selection dialog
                project_dialog = ctk.CTkToplevel(dialog)
                project_dialog.title("Select Project")
                project_dialog.geometry("400x600")  # Increased from 300x450
                project_dialog.transient(dialog)
                
                # Make sure the dialog is visible before setting grab
                project_dialog.update_idletasks()
                project_dialog.deiconify()
                project_dialog.wait_visibility()
                project_dialog.lift()
                project_dialog.focus_force()
                
                # Center the dialog on the parent dialog
                x = dialog.winfo_x() + (dialog.winfo_width() // 2) - (400 // 2)
                y = dialog.winfo_y() + (dialog.winfo_height() // 2) - (600 // 2)
                project_dialog.geometry(f"+{x}+{y}")
                
                # Now that the window is visible, set grab
                project_dialog.grab_set()
                
                # Add window close protocol handler
                def on_project_dialog_close():
                    try:
                        # Any cleanup needed for project dialog
                        pass
                    except Exception:
                        # Ignore any errors during cleanup
                        pass
                    finally:
                        # Always destroy the dialog
                        project_dialog.destroy()
                
                project_dialog.protocol("WM_DELETE_WINDOW", on_project_dialog_close)
                
                # Add label
                ctk.CTkLabel(
                    project_dialog,
                    text="Available Projects:",
                    font=("Helvetica", 14, "bold")
                ).pack(padx=20, pady=(10, 5))
                
                # Add filter controls
                filter_frame = ctk.CTkFrame(project_dialog)
                filter_frame.pack(fill="x", padx=20, pady=5)
                
                ctk.CTkLabel(filter_frame, text="Filter:").pack(side="left", padx=(0, 5))
                filter_var = ctk.StringVar()
                filter_entry = ctk.CTkEntry(filter_frame, textvariable=filter_var)
                filter_entry.pack(side="left", fill="x", expand=True)
                
                # Create a placeholder for the update_project_list function
                def update_project_list(*args):
                    pass
                
                # Add checkbox for AZR projects
                azr_only_var = ctk.BooleanVar(value=True)
                azr_checkbox = ctk.CTkCheckBox(filter_frame, text="Show only AZR projects", variable=azr_only_var, 
                                              command=lambda: update_project_list())
                azr_checkbox.pack(side="left", padx=5)
                
                # Create frame for the project buttons
                projects_frame = ctk.CTkScrollableFrame(project_dialog, height=300)
                projects_frame.pack(fill="both", expand=True, padx=20, pady=10)
                
                # Keep reference to projects frame
                dialog.projects_frame = projects_frame
                
                # Store project names and IDs
                dialog.all_projects = []
                for p in projects:
                    # Check if it's a dictionary with 'name' and 'id' keys
                    if isinstance(p, dict) and 'name' in p and 'id' in p:
                        dialog.all_projects.append({'name': p['name'], 'id': p['id']})
                    # Or just a simple string name
                    elif isinstance(p, str):
                        # In this case, we'll need to find the ID later
                        dialog.all_projects.append({'name': p, 'id': None})
                
                # Redefine the function to update project list based on filter
                def update_project_list(*args):
                    # Clear existing buttons
                    for widget in projects_frame.winfo_children():
                        widget.destroy()
                    
                    # Get filter text
                    filter_text = filter_var.get().lower()
                    azr_only = azr_only_var.get()
                    
                    # Add filtered projects
                    for project in dialog.all_projects:
                        project_name = project['name']
                        
                        # Check if project passes both filters
                        text_match = filter_text in project_name.lower()
                        azr_match = not azr_only or project_name.startswith("AZR-")
                        
                        if text_match and azr_match:
                            project_btn = ctk.CTkButton(
                                projects_frame,
                                text=project_name,
                                command=lambda p=project: select_project(p)
                            )
                            project_btn.pack(fill="x", pady=2)
                
                # Function to select a project
                def select_project(project):
                    # Default detected environment
                    detected_env = "TEST"
                    
                    # Try to auto-detect environment from base URL
                    base_url = self.config_manager.config.get("base_url", "")
                    if base_url and "." in base_url:
                        parts = base_url.split(".")
                        if parts[0]:
                            detected_env = parts[0].upper()
                    
                    # Get the project ID if it's not already set
                    project_id = project['id']
                    if project_id is None:
                        status_var.set(f"Looking up ID for project {project['name']}...")
                        dialog.update_idletasks()  # Force UI update
                        # Find the ID from folder structure
                        project_id = self.find_folder_id_by_name(folder_structure, project['name'])
                        if not project_id:
                            status_var.set(f"Could not find folder ID for {project['name']}")
                            return
                        project['id'] = project_id
                    
                    # Now get environments for this project
                    status_var.set(f"Retrieving environments for {project['name']}...")
                    dialog.update_idletasks()  # Force UI update
                    folder_id = project_id
                    folder_contents = client.get_folder(folder_id)
                    subfolders = self.get_subfolders(folder_contents)
                    
                    # Update environment dropdown with actual values from the project
                    env_values = [folder['name'] for folder in subfolders] if isinstance(subfolders[0], dict) else subfolders
                    
                    # Filter out environments that start with "INFRA-"
                    filtered_env_values = [env for env in env_values if not env.startswith("INFRA-")]
                    
                    env_combo.configure(values=filtered_env_values)
                    
                    # Check if our detected environment exists in the available environments
                    detected_env_exists = False
                    for env in filtered_env_values:
                        if env == detected_env:  # Exact match only
                            detected_env_exists = True
                            break
                    
                    # Set the environment value
                    if filtered_env_values:
                        if detected_env_exists:
                            env_var.set(detected_env)  # Set our detected environment if it exists
                            print(f"Setting detected environment: {detected_env}")
                        else:
                            env_var.set(filtered_env_values[0])  # Otherwise use the first available environment
                            print(f"Detected environment '{detected_env}' not found, using: {filtered_env_values[0]}")
                    
                    # Store folder contents for later use
                    dialog.folder_contents = folder_contents
                    
                    # Close the project dialog
                    project_dialog.destroy()
                    
                    # Update the dialog state with the selected project
                    dialog.selected_project = project['name']
                    
                    # Enable get password button
                    get_password_btn.configure(state="normal")
                    
                    # Update status
                    status_var.set(f"Selected project: {project['name']} with {len(filtered_env_values)} environments")
                
                # Add trace after defining the function
                filter_var.trace_add("write", lambda *args: update_project_list())
                
                # Initial update of project list
                update_project_list()
                
            except Exception as e:
                status_var.set(f"Error detecting projects: {str(e)}")
                import traceback
                traceback.print_exc()
                
        # Connect to KeePass and get environments
        def connect():
            try:
                # Skip the "Connecting to KeePass..." message since we're already connected
                if not hasattr(dialog, 'client'):
                    status_var.set("No KeePass connection yet!")
                    return
                
                client = dialog.client
                
                status_var.set("Loading...")
                dialog.update()  # Force complete UI update
                
                # Get project folder
                projects_folder_id = "87300a24-9741-4d24-8a5c-a8b04e0b7049"
                folder_structure = client.get_folder(projects_folder_id)
                
                # Try to determine project name AND environment from the base URL automatically
                project_name = "AZR-CSE"  # Default project
                detected_env = "TEST"  # Default environment
                
                status_var.set("Scanning...")
                dialog.update()  # Force complete UI update
                
                base_url = self.config_manager.config.get("base_url", "")
                
                if base_url and "." in base_url:
                    parts = base_url.split(".")
                    
                    # Extract environment directly from first part (before first dot)
                    if parts[0]:
                        # Just use the exact environment name from the URL (uppercase)
                        detected_env = parts[0].upper()
                        print(f"Auto-detected environment from URL: {detected_env}")
                    
                    # Extract project name from second part (between first and second dot)
                    if len(parts) >= 2 and parts[1]:
                        # Extract second part of domain and add AZR- prefix
                        detected_project = parts[1].upper()
                        project_name = f"AZR-{detected_project}"
                        print(f"Auto-detected project name from URL: {project_name}")
                
                status_var.set("Searching...")
                dialog.update()  # Force complete UI update
                
                folder_id = self.find_folder_id_by_name(folder_structure, project_name)
                
                if not folder_id:
                    status_var.set(f"Folder '{project_name}' not found! Click 'Detect Projects' to choose manually.")
                    detect_projects_btn.configure(state="normal")
                    return
                
                # Get environments for this project
                status_var.set("Processing...")
                dialog.update()  # Force complete UI update
                
                folder_contents = client.get_folder(folder_id)
                subfolders = self.get_subfolders(folder_contents)
                
                # Update environment dropdown with actual values from the project
                env_values = [folder['name'] for folder in subfolders] if isinstance(subfolders[0], dict) else subfolders
                
                # Filter out environments that start with "INFRA-"
                filtered_env_values = [env for env in env_values if not env.startswith("INFRA-")]
                
                env_combo.configure(values=filtered_env_values)
                
                # Check if our detected environment exists in the available environments
                detected_env_exists = False
                for env in filtered_env_values:
                    if env == detected_env:  # Exact match only
                        detected_env_exists = True
                        break
                
                # Set the environment value
                if filtered_env_values:
                    if detected_env_exists:
                        env_var.set(detected_env)  # Set our detected environment if it exists
                        print(f"Setting detected environment: {detected_env}")
                    else:
                        env_var.set(filtered_env_values[0])  # Otherwise use the first available environment
                        print(f"Detected environment '{detected_env}' not found, using: {filtered_env_values[0]}")
                
                # Store folder contents for later use
                dialog.folder_contents = folder_contents
                
                # Store project name for later use
                dialog.selected_project = project_name
                
                # Store folder structure for recursive search
                dialog.folder_structure = folder_structure
                
                # Update status with Environment Autodetect message
                status_var.set(f"Environment Autodetected - {project_name} - {env_var.get()}")
                
                # Enable environment selection ComboBox
                env_combo.configure(state="normal")
                
                # Enable get password button
                get_password_btn.configure(state="normal")
                
                # Also enable detect projects button in case user wants to select a different project
                detect_projects_btn.configure(state="normal")
                
            except Exception as e:
                status_var.set(f"Connection error: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Function to get password
        def get_password():
            try:
                # Determine which project is selected
                if not hasattr(dialog, 'selected_project'):
                    # Try to auto-determine project from URL
                    status_var.set("No project selected. Attempting to auto-detect project...")
                    dialog.update_idletasks()  # Force UI update
                    connect()
                    if not hasattr(dialog, 'selected_project'):
                        status_var.set("No project selected! Click 'Detect Projects' to select a project.")
                        return
                
                project_name = dialog.selected_project
                environment = env_var.get()
                
                status_var.set("Retrieving...")
                dialog.update()  # Force complete UI update
                
                # Clear any existing password
                target_entry.delete(0, 'end')
                
                client = dialog.client
                
                # If we have folder_contents, use that instead of making more API calls
                if hasattr(dialog, 'folder_contents'):
                    folder_contents = dialog.folder_contents
                    
                    # Find the selected environment in folder_contents
                    env_folder = None
                    for folder in self.get_subfolders(folder_contents):
                        if isinstance(folder, dict) and folder.get('name') == environment:
                            env_folder = folder
                            break
                        elif folder == environment:  # String comparison
                            # Need to get the ID for this environment
                            env_id = self.find_folder_id_by_name(folder_contents, environment)
                            if env_id:
                                env_folder = client.get_folder(env_id)
                            break
                    
                    if env_folder:
                        # Get full environment folder structure
                        env_id = env_folder['id'] if isinstance(env_folder, dict) else env_folder
                        env_structure = client.get_folder(env_id)
                        
                        # Find the credential in this environment based on password type
                        if password_type == "basic_auth":
                            entry = self.find_basic_auth_password_entry(env_structure)
                        else:  # webdav_admin
                            entry = self.find_webdav_admin_password_entry(env_structure)
                        
                        if entry:
                            try:
                                # Get the password
                                if isinstance(entry, dict) and 'Id' in entry:
                                    # Direct API call to get the password
                                    password_url = f"credentials/{entry['Id']}/password"
                                    print(f"Making API call to: {password_url}")
                                    password = client._make_request('GET', password_url)
                                    # Set password in the target entry field
                                    target_entry.delete(0, 'end')
                                    target_entry.insert(0, str(password).strip())
                                    status_var.set(f"Retrieved credential successfully!")
                                elif hasattr(entry, 'password'):
                                    # For backwards compatibility, try to access password as attribute
                                    password = entry.password
                                    target_entry.delete(0, 'end')
                                    target_entry.insert(0, password)
                                    status_var.set(f"Retrieved credential successfully!")
                                else:
                                    status_var.set(f"Error: Unsupported entry format")
                                    print(f"Unsupported entry format: {type(entry)}")
                                    return
                                
                                # Close the dialog after successful retrieval
                                dialog.after(2000, on_dialog_close)
                            except Exception as e:
                                status_var.set(f"Error retrieving password: {str(e)}")
                                print(f"Error getting password: {str(e)}")
                        else:
                            status_var.set(f"No credentials found in {environment}!")
                    else:
                        status_var.set(f"Environment {environment} not found in project {project_name}!")
                else:
                    # Fallback to the previous implementation if folder_contents is not available
                    folder_structure = dialog.folder_structure if hasattr(dialog, 'folder_structure') else client.get_folder("87300a24-9741-4d24-8a5c-a8b04e0b7049")
                    
                    # Navigate to project folder
                    project_folder_id = self.find_folder_id_by_name(folder_structure, project_name)
                    
                    if not project_folder_id:
                        status_var.set(f"Project '{project_name}' not found!")
                        return
                    
                    # Get project folder structure
                    project_folder = client.get_folder(project_folder_id)
                    
                    # Find environment folder
                    env_folder_id = self.find_folder_id_by_name(project_folder, environment)
                    
                    if not env_folder_id:
                        status_var.set(f"Environment '{environment}' not found!")
                        return
                    
                    # Get environment folder structure
                    env_folder = client.get_folder(env_folder_id)
                    
                    # Find the credential in this environment based on password type
                    if password_type == "basic_auth":
                        entry = self.find_basic_auth_password_entry(env_folder)
                    else:  # webdav_admin
                        entry = self.find_webdav_admin_password_entry(env_folder)
                    
                    if entry:
                        try:
                            # Get the password - entry might be a dict, not an object with a password attribute
                            if isinstance(entry, dict) and 'Id' in entry:
                                # Direct API call to get the password
                                password_url = f"credentials/{entry['Id']}/password"
                                print(f"Making API call to: {password_url}")
                                password = client._make_request('GET', password_url)
                                # Set password in the target entry field
                                target_entry.delete(0, 'end')
                                target_entry.insert(0, str(password).strip())
                                status_var.set(f"Retrieved credential successfully!")
                            elif hasattr(entry, 'password'):
                                # For backwards compatibility, try to access password as attribute
                                password = entry.password
                                target_entry.delete(0, 'end')
                                target_entry.insert(0, password)
                                status_var.set(f"Retrieved credential successfully!")
                            else:
                                status_var.set(f"Error: Unsupported entry format")
                                print(f"Unsupported entry format: {type(entry)}")
                                return
                            
                            # Close the dialog after successful retrieval
                            dialog.after(2000, on_dialog_close)
                        except Exception as e:
                            status_var.set(f"Error retrieving password: {str(e)}")
                            print(f"Error getting password: {str(e)}")
                    else:
                        status_var.set(f"No credentials found for this project/environment!")
            
            except Exception as e:
                status_var.set(f"Error: {str(e)}")
                import traceback
                traceback.print_exc()
    
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
        """Create a tooltip for a widget"""
        # Improved tooltip implementation with delay and better cleanup
        tooltip_id = None  # For tracking the scheduled tooltip
        tooltip_window = None  # For tracking the tooltip window
        
        def show_tooltip(x, y):
            nonlocal tooltip_window
            # If there's already a tooltip showing, destroy it first
            if tooltip_window is not None:
                try:
                    tooltip_window.destroy()
                except:
                    pass
            
            # Create a toplevel window for the tooltip
            tooltip_window = ctk.CTkToplevel(self.root)
            tooltip_window.wm_overrideredirect(True)  # Remove window decorations
            tooltip_window.wm_geometry(f"+{x+15}+{y+10}")
            tooltip_window.attributes("-topmost", True)  # Keep tooltip on top
            
            # Create a label with the tooltip text
            label = ctk.CTkLabel(
                tooltip_window,
                text=text,
                corner_radius=6,
                fg_color=("#333333", "#666666"),  # Dark background
                text_color=("#FFFFFF", "#FFFFFF"),  # White text
                padx=10,
                pady=5
            )
            label.pack()
            
            # Store the tooltip reference in the widget
            widget._tooltip_window = tooltip_window
        
        # When mouse enters the widget, schedule tooltip display
        def enter(event):
            nonlocal tooltip_id
            # Cancel any existing scheduled tooltip
            if tooltip_id is not None:
                widget.after_cancel(tooltip_id)
                tooltip_id = None
            
            # Schedule new tooltip with a small delay (300ms)
            tooltip_id = widget.after(300, lambda: show_tooltip(event.x_root, event.y_root))
            
        # When mouse leaves the widget, cancel scheduled tooltip and hide existing one
        def leave(event):
            nonlocal tooltip_id, tooltip_window
            # Cancel any scheduled tooltip
            if tooltip_id is not None:
                widget.after_cancel(tooltip_id)
                tooltip_id = None
            
            # Destroy any existing tooltip
            if tooltip_window is not None:
                try:
                    tooltip_window.destroy()
                except:
                    pass
                tooltip_window = None
            
            # Also check for the old tooltip attribute for backward compatibility
            if hasattr(widget, "_tooltip_window"):
                try:
                    widget._tooltip_window.destroy()
                except:
                    pass
                delattr(widget, "_tooltip_window")
        
        # Bind events
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
        
        # Also bind to window close to ensure tooltips are cleaned up
        # Use a safer approach that doesn't trigger errors
        def safe_leave(event):
            try:
                leave(event)
            except:
                pass
                
        self.root.bind("<Destroy>", safe_leave, add="+")

    def run(self):
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
        """Handle platform change"""
        platform = self.platform_var.get()
        
        # Update the base install directory based on platform
        if platform == "Windows":
            default_dir = "C:\\gkretail"
            firebird_path = "C:\\Program Files\\Firebird\\Firebird_3_0"
            jaybird_driver_path = "C:\\gkretail\\Jaybird"
            default_detection_dir = "C:\\gkretail\\stations"  # Add default detection directory
        else:  # Linux
            default_dir = "/usr/local/gkretail"
            firebird_path = "/opt/firebird"
            jaybird_driver_path = "/usr/local/gkretail/Jaybird"
            default_detection_dir = "/usr/local/gkretail/stations"  # Add default detection directory
        
        # Update config values first
        self.config_manager.config["base_install_dir"] = default_dir
        self.config_manager.config["firebird_server_path"] = firebird_path
        self.config_manager.config["firebird_driver_path_local"] = jaybird_driver_path
        
        # Always update the entry field to match config
        base_dir_entry = self.config_manager.get_entry("base_install_dir")
        if base_dir_entry:
            base_dir_entry.delete(0, 'end')
            base_dir_entry.insert(0, self.config_manager.config["base_install_dir"])
        
        firebird_path_entry = self.config_manager.get_entry("firebird_server_path")
        if firebird_path_entry:
            firebird_path_entry.delete(0, 'end')
            firebird_path_entry.insert(0, firebird_path)
            
        jaybird_path_entry = self.config_manager.get_entry("firebird_driver_path_local")
        if jaybird_path_entry:
            jaybird_path_entry.delete(0, 'end')
            jaybird_path_entry.insert(0, jaybird_driver_path)
            
        # Update entries using the config manager method (may be redundant but ensures consistency)
        self.config_manager.update_entry_value("base_install_dir", default_dir)
        self.config_manager.update_entry_value("firebird_server_path", firebird_path)
        self.config_manager.update_entry_value("firebird_driver_path_local", jaybird_driver_path)
        
        print(f"Platform changed to {platform}, updated base_install_dir to {default_dir}, firebird_server_path to {firebird_path}, and firebird_driver_path_local to {jaybird_driver_path}")
        
        # UPDATE DETECTION SETTINGS: If detection config exists, update the base directory
        if "detection_config" in self.config_manager.config:
            # Get the current detection config
            detection_config = self.config_manager.config["detection_config"]
            
            # Update the base directory in detection_config
            if detection_config.get("use_base_directory", True):
                detection_config["base_directory"] = default_detection_dir
                print(f"Updated detection base directory to: {default_detection_dir}")
                
                # Update detection manager with the new config
                self.detection_manager.set_config(detection_config)
                
                # If detection settings window is open, update its UI
                if hasattr(self, 'detection_window') and self.detection_window is not None and self.detection_window.winfo_exists():
                    # Update base directory entry if it exists
                    if hasattr(self, 'base_dir_entry') and self.base_dir_entry.winfo_exists():
                        self.base_dir_entry.delete(0, 'end')
                        self.base_dir_entry.insert(0, default_detection_dir)
        
        # Update config
        self.config_manager.config["platform"] = platform
        self.config_manager.save_config_silent()

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
        tab_file_detection = tabview.add("File Detection")
        tab_regex = tabview.add("Hostname Detection")
        
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
        
        ctk.CTkLabel(
            note_frame,
            text="Important: Your regex must include exactly two capture groups:",
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

            # Update the pattern in the detection manager
            self.detection_manager.set_hostname_regex(regex_pattern, platform)
            self.detection_manager.set_test_hostname(hostname)

            # Test the regex
            result = self.detection_manager.test_hostname_regex(hostname, platform)

            # Display the results
            results_text.configure(state="normal")
            results_text.delete("1.0", "end")

            if result["success"]:
                # Success case
                results_text.insert("1.0", f"✅ Match successful!\n\n")

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
        
        # Create WebDAV browser
        self.create_webdav_browser()
        
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
        
        # WebDAV connection prompt
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
            text="Connect to WebDAV first to download components",
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
            text="Please connect to WebDAV before creating packages",
            font=("Helvetica", 12),
            text_color="#FF9E3D"  # Orange for warning
        )
        self.status_label.pack(pady=5, padx=10)
    
    def create_webdav_browser(self):
        # Create WebDAV browser frame with a subtle gradient background
        webdav_frame = ctk.CTkFrame(self.main_frame)
        webdav_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Header section with modern design
        header_frame = ctk.CTkFrame(webdav_frame, fg_color="#1E2433")
        header_frame.pack(fill="x", padx=5, pady=5)
        
        # Title with icon
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(side="left", padx=10, fill="y")
        
        # WebDAV icon label
        icon_label = ctk.CTkLabel(
            title_frame,
            text="🌐",
            font=("Helvetica", 18)
        )
        icon_label.pack(side="left", padx=(0, 5))
        
        # Title
        title_label = ctk.CTkLabel(
            title_frame,
            text="DSG WebDAV Browser",
            font=("Helvetica", 16, "bold"),
            text_color="#4D90FE"  # Professional blue color
        )
        title_label.pack(side="left", padx=5)
        
        # Current path with a modern look
        path_frame = ctk.CTkFrame(header_frame, fg_color="#2A3343", corner_radius=6)
        path_frame.pack(side="right", padx=10, pady=5, fill="y")
        
        folder_icon = ctk.CTkLabel(
            path_frame,
            text="📂",
            font=("Helvetica", 14)
        )
        folder_icon.pack(side="left", padx=(5, 0))
        
        self.path_label = ctk.CTkLabel(
            path_frame,
            text="/SoftwarePackage",
            font=("Helvetica", 12),
            text_color="#E0E0E0"
        )
        self.path_label.pack(side="right", padx=(0, 10))
        
        # Authentication section with better styling
        auth_frame = ctk.CTkFrame(webdav_frame)
        auth_frame.pack(fill="x", padx=5, pady=5)
        
        # Username with icon
        username_frame = ctk.CTkFrame(auth_frame, fg_color="transparent")
        username_frame.pack(side="left", padx=5)
        
        username_icon = ctk.CTkLabel(username_frame, text="👤", width=25)
        username_icon.pack(side="left", padx=(0, 2))
        
        username_label = ctk.CTkLabel(username_frame, text="Username:", width=75)
        username_label.pack(side="left", padx=2)
        
        self.webdav_username = ctk.CTkEntry(auth_frame, width=120, corner_radius=6)
        self.webdav_username.pack(side="left", padx=5)
        
        # Load saved username
        if self.config_manager.config.get("webdav_username"):
            self.webdav_username.insert(0, self.config_manager.config["webdav_username"])
        
        # Register WebDAV username with config manager
        self.config_manager.register_entry("webdav_username", self.webdav_username)
        
        # Password with icon
        password_frame = ctk.CTkFrame(auth_frame, fg_color="transparent")
        password_frame.pack(side="left", padx=5)
        
        password_icon = ctk.CTkLabel(password_frame, text="🔒", width=25)
        password_icon.pack(side="left", padx=(0, 2))
        
        password_label = ctk.CTkLabel(password_frame, text="Password:", width=75)
        password_label.pack(side="left", padx=2)
        
        # Create a flag to track password visibility state
        self.password_visible = False
        
        # Password entry
        self.webdav_password = ctk.CTkEntry(auth_frame, width=120, show="•", corner_radius=6)
        self.webdav_password.pack(side="left", padx=5)
        
        # Load saved password
        if self.config_manager.config.get("webdav_password"):
            self.webdav_password.insert(0, self.config_manager.config["webdav_password"])
        
        # Add show/hide password button
        self.password_toggle_btn = ctk.CTkButton(
            auth_frame,
            text="👁️",
            width=35,
            height=28,
            corner_radius=6,
            fg_color="#3D4D65",
            hover_color="#4D5D75",
            command=self.toggle_password_visibility
        )
        self.password_toggle_btn.pack(side="left", padx=(0, 5))
        
        # KeePass button with improved styling
        keepass_btn = ctk.CTkButton(
            auth_frame,
            text="🔑",
            width=35,
            height=28,
            corner_radius=6,
            fg_color="#3D4D65",
            hover_color="#4D5D75",
            command=lambda: self.get_basic_auth_password_from_keepass(
                target_entry=self.webdav_password, 
                password_type="webdav_admin"
            )
        )
        keepass_btn.pack(side="left", padx=5)
        
        # Register WebDAV password with config manager
        self.config_manager.register_entry("webdav_password", self.webdav_password)
        
        # Connect button with modern styling
        connect_btn = ctk.CTkButton(
            auth_frame,
            text="Connect",
            width=85,
            height=28,
            corner_radius=6,
            fg_color="#2B5BA0",
            hover_color="#3A6AB0",
            command=self.connect_webdav
        )
        connect_btn.pack(side="left", padx=10)
        
        # Status with badge style
        status_frame = ctk.CTkFrame(auth_frame, fg_color="transparent")
        status_frame.pack(side="left", padx=10)
        
        status_label = ctk.CTkLabel(status_frame, text="Status:", width=50)
        status_label.pack(side="left", padx=2)
        
        self.webdav_status = ctk.CTkLabel(
            status_frame,
            text="Not Connected",
            text_color="#FF6B6B",
            font=("Helvetica", 12, "bold")
        )
        self.webdav_status.pack(side="left", padx=5)
        
        # Navigation section with better styling
        nav_frame = ctk.CTkFrame(webdav_frame)
        nav_frame.pack(fill="x", padx=5, pady=5)
        
        # Button group with consistent styling
        button_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
        button_frame.pack(side="left", padx=5)
        
        # Up button
        up_btn = ctk.CTkButton(
            button_frame,
            text="⬆️ Up",
            width=60,
            height=28,
            corner_radius=6,
            fg_color="#3D4D65",
            hover_color="#4D5D75",
            command=self.navigate_up
        )
        up_btn.pack(side="left", padx=(0, 5))
        
        # Refresh button
        refresh_btn = ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            width=85,
            height=28,
            corner_radius=6,
            fg_color="#3D4D65",
            hover_color="#4D5D75",
            command=self.refresh_listing
        )
        refresh_btn.pack(side="left", padx=5)
        
        # Directory listing - enhanced with styled Listbox and custom Frame
        dir_listing_frame = ctk.CTkFrame(webdav_frame, fg_color="#202837", corner_radius=8)
        dir_listing_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add a header
        list_header_frame = ctk.CTkFrame(dir_listing_frame, fg_color="#272E3F", corner_radius=0)
        list_header_frame.pack(fill="x", padx=0, pady=0)
        
        ctk.CTkLabel(
            list_header_frame,
            text="Name",
            font=("Helvetica", 12, "bold"),
            text_color="#CCCCCC",
        ).pack(side="left", padx=10, pady=8)
        
        # Use tkinter Listbox with enhanced styling
        import tkinter as tk
        from tkinter import ttk
        
        # Create style for the scrollbar
        style = ttk.Style()
        style.configure("Vertical.TScrollbar", 
                        background="#3D4D65", 
                        troughcolor="#202837", 
                        arrowcolor="#FFFFFF")
        
        # Create a Frame for the Listbox and scrollbar
        listbox_frame = ctk.CTkFrame(dir_listing_frame, fg_color="transparent")
        listbox_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Create a scrollbar with custom styling
        scrollbar = ttk.Scrollbar(listbox_frame, style="Vertical.TScrollbar")
        scrollbar.pack(side="right", fill="y")
        
        # Create the Listbox with enhanced styling
        self.dir_list = tk.Listbox(
            listbox_frame,
            yscrollcommand=scrollbar.set,
            bg="#1A2332",  # Darker blue background
            fg="#E0E0E0",  # Light gray text
            selectbackground="#3D5B94",  # Highlight blue
            selectforeground="#FFFFFF",  # White text for selection
            font=("Segoe UI", 11),  # Modern font
            height=15,
            borderwidth=0,
            highlightthickness=0,
            activestyle="none"  # Remove dotted line around selected item
        )
        self.dir_list.pack(side="left", fill="both", expand=True)
        
        # Configure the scrollbar
        scrollbar.config(command=self.dir_list.yview)
        
        # Bind events for better interaction
        self.dir_list.bind("<Double-1>", self.on_item_double_click)
        self.dir_list.bind("<Return>", self.on_item_double_click)  # Also allow Enter key
    
    def refresh_listing(self):
        """Refresh directory listing with enhanced styling"""
        # Clear the listbox
        self.dir_list.delete(0, "end")
        
        try:
            # Get all items
            items = self.webdav.list_directories(self.webdav.current_path)
            
            # Update path label
            self.path_label.configure(text=self.webdav.current_path)
            
            # Sort items - directories first, then files
            items.sort(key=lambda x: (not x['is_directory'], x['name'].lower()))
            
            # Store items for reference when clicking
            self.current_items = items
            
            # Add items to listbox with different icons for different file types
            for item in items:
                # Choose appropriate icon based on type
                if item['is_directory']:
                    icon = "📁"
                elif item['name'].lower().endswith(('.zip', '.tar', '.gz', '.rar')):
                    icon = "📦"
                elif item['name'].lower().endswith(('.exe', '.msi', '.bat', '.sh')):
                    icon = "⚙️"
                elif item['name'].lower().endswith(('.xml', '.json', '.yaml', '.yml')):
                    icon = "📄"
                elif item['name'].lower().endswith(('.jar', '.war')):
                    icon = "☕"
                else:
                    icon = "📄"
                
                self.dir_list.insert("end", f"{icon}  {item['name']}")
                
            # Set different colors for directories and files
            for i, item in enumerate(items):
                if item['is_directory']:
                    self.dir_list.itemconfig(i, {'fg': '#4D90FE'})  # Bright blue for directories
                elif item['name'].lower().endswith(('.jar', '.war')):
                    self.dir_list.itemconfig(i, {'fg': '#FF9E3D'})  # Orange for Java files
                elif item['name'].lower().endswith(('.exe', '.msi', '.bat', '.sh')):
                    self.dir_list.itemconfig(i, {'fg': '#53D86A'})  # Green for executables
                
            # If no items found, display a message
            if not items:
                self.dir_list.insert("end", "  (Empty directory)")
                self.dir_list.itemconfig(0, {'fg': '#8C8C8C'})  # Gray for empty message
                    
        except Exception as e:
            self.webdav_status.configure(text=f"Error: {str(e)}", text_color="#FF6B6B")
            self.dir_list.insert("end", "  Error: Could not retrieve directory listing")
            self.dir_list.itemconfig(0, {'fg': '#FF6B6B'})  # Red for error message
    
    def connect_webdav(self):
        """Handle WebDAV connection with improved feedback"""
        base_url = self.config_manager.config["base_url"]
        username = self.webdav_username.get()
        password = self.webdav_password.get()
        
        if not all([base_url, username, password]):
            self.webdav_status.configure(
                text="Missing credentials",
                text_color="#FF6B6B"
            )
            return
        
        # Show connecting status
        self.webdav_status.configure(text="Connecting...", text_color="#FFD700")
        self.window.update_idletasks()  # Update the UI to show the connecting message
        
        # Create WebDAV browser instance
        self.webdav = self.project_generator.create_webdav_browser(
            base_url,
            username,
            password
        )
        
        # Connect to WebDAV server
        success, message = self.webdav.connect()
        
        if success:
            self.webdav_status.configure(text="Connected", text_color="#53D86A")  # Green for success
            
            # Save credentials to config
            self.config_manager.config["webdav_username"] = username
            self.config_manager.config["webdav_password"] = password
            self.config_manager.save_config_silent()
            
            # Enable create offline package button with visual indicator
            self.create_button.configure(
                state="normal",
                fg_color="#2B5BA0",  # Normal blue color
                hover_color="#3A6AB0"  # Hover blue color
            )
            
            # Clear the connection prompt and update status label
            if hasattr(self, 'connection_prompt'):
                self.connection_prompt.configure(
                    text="WebDAV connected successfully",
                    text_color="#53D86A"  # Green for success
                )
            
            # Update the status label
            self.status_label.configure(
                text="Ready to create offline packages",
                text_color="#53D86A"  # Green for success
            )
            
            # Navigate to SoftwarePackage directory
            self.webdav.current_path = "/SoftwarePackage"
            self.refresh_listing()
        else:
            self.webdav_status.configure(text=f"Connection failed", text_color="#FF6B6B")  # Red for error
            
            # Show specific error in a tooltip or status label
            error_msg = message if len(message) < 50 else message[:47] + "..."
            self.status_label.configure(text=f"WebDAV: {error_msg}", text_color="#FF6B6B")
    
    def create_offline_package(self):
        """Create offline package with selected components"""
        try:
            # Check if WebDAV is connected
            if not hasattr(self, 'webdav') or not getattr(self.webdav, 'connected', False):
                self.show_error("WebDAV Connection Required", "Please Connect first to WebDAV before proceeding.")
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
        """Enter a directory"""
        new_path = os.path.join(self.webdav.current_path, dirname)
        self.webdav.current_path = new_path
        self.refresh_listing()
    
    def navigate_up(self):
        """Navigate to parent directory"""
        if self.webdav.current_path != "/":
            self.webdav.current_path = os.path.dirname(self.webdav.current_path.rstrip('/'))
            self.refresh_listing()
    
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