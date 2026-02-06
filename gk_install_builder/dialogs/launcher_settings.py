"""
Launcher Settings Editor dialog for Store-Install-Builder
"""
import os
from tkinter import messagebox
import customtkinter as ctk

try:
    from gk_install_builder.ui.helpers import bind_mousewheel_to_frame
    from gk_install_builder.utils.tooltips import create_tooltip
except ImportError:
    from ui.helpers import bind_mousewheel_to_frame
    from utils.tooltips import create_tooltip


class LauncherSettingsEditor:
    """Dialog for editing launcher configuration templates for different components"""

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
        """Open the launcher settings editor window"""
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

        component_types = ["POS", "ONEX-POS", "WDM", "FLOW-SERVICE", "LPA-SERVICE", "STOREHUB-SERVICE", "RCS-SERVICE"]

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
                    create_tooltip(label, self.parameter_tooltips[key], parent_window=self.window)
                    create_tooltip(entry, self.parameter_tooltips[key], parent_window=self.window)

                # Store the entry widget in the settings dictionary
                self.settings[component_type][key] = {"value": value, "entry": entry}

                row += 1

            # Add RCS HTTPS checkbox to the RCS-SERVICE tab
            if component_type == "RCS-SERVICE":
                separator = ctk.CTkFrame(scrollable_settings, height=2, fg_color="gray50")
                separator.grid(row=row, column=0, sticky="ew", padx=5, pady=10)
                row += 1

                https_frame = ctk.CTkFrame(scrollable_settings, fg_color="transparent")
                https_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)

                self.rcs_use_https_var = ctk.BooleanVar(
                    value=self.config_manager.config.get("rcs_use_https", False)
                )
                rcs_https_cb = ctk.CTkCheckBox(
                    https_frame,
                    text="Use HTTPS for RCS URL",
                    variable=self.rcs_use_https_var,
                    onvalue=True, offvalue=False
                )
                rcs_https_cb.pack(side="left", padx=10, pady=5)
                create_tooltip(rcs_https_cb,
                    "Use HTTPS protocol and HTTPS port for the RCS service URL.\n"
                    "When enabled, the store-initialization script will configure\n"
                    "RCS with https://<hostname>:<httpsPort>/rcs instead of\n"
                    "http://<hostname>:<httpPort>/rcs.",
                    parent_window=self.window)

                skip_url_frame = ctk.CTkFrame(scrollable_settings, fg_color="transparent")
                skip_url_frame.grid(row=row + 1, column=0, sticky="ew", padx=5, pady=5)

                self.rcs_skip_url_var = ctk.BooleanVar(
                    value=self.config_manager.config.get("rcs_skip_url_config", False)
                )
                rcs_skip_url_cb = ctk.CTkCheckBox(
                    skip_url_frame,
                    text="Don't set RCS URL",
                    variable=self.rcs_skip_url_var,
                    onvalue=True, offvalue=False
                )
                rcs_skip_url_cb.pack(side="left", padx=10, pady=5)
                create_tooltip(rcs_skip_url_cb,
                    "Skip setting the RCS URL during store initialization.\n"
                    "When enabled, the store-initialization script will not\n"
                    "make the API call to configure the rcs.url property\n"
                    "in Config-Service.",
                    parent_window=self.window)

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

        # OneX POS settings (same JMX ports as POS - mutually exclusive)
        self.settings["ONEX-POS"] = {
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

        # RCS Service settings
        self.settings["RCS-SERVICE"] = {
            "applicationServerHttpPort": "8180",
            "applicationServerHttpsPort": "8543",
            "applicationServerShutdownPort": "8005",
            "applicationServerJmxPort": "52222",
            "updaterJmxPort": "4333",
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
            "ONEX-POS": "launcher.onex-pos.template",
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

        # Save RCS settings
        if hasattr(self, 'rcs_use_https_var'):
            self.config_manager.config["rcs_use_https"] = self.rcs_use_https_var.get()
        if hasattr(self, 'rcs_skip_url_var'):
            self.config_manager.config["rcs_skip_url_config"] = self.rcs_skip_url_var.get()

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
