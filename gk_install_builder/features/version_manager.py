import customtkinter as ctk

try:
    from gk_install_builder.utils.tooltips import create_tooltip
except ImportError:
    from utils.tooltips import create_tooltip

class VersionManager:
    """Manages version configuration UI for components"""

    def __init__(self, parent_window, config_manager, api_client, main_frame):
        self.root = parent_window
        self.config_manager = config_manager
        self.api_client = api_client
        self.main_frame = main_frame

        # Version field references for show/hide functionality
        self.version_fields = []

        # Version entry references
        self.pos_version_entry = None
        self.wdm_version_entry = None
        self.flow_service_version_entry = None
        self.lpa_service_version_entry = None
        self.storehub_service_version_entry = None

        # Checkbox variables
        self.version_override_var = None
        self.use_default_versions_var = None
        self.version_source_var = None

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        return create_tooltip(widget, text, parent_window=self.root)

    def create_component_versions(self):
        """Create component version UI section"""
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
        # NOTE: CONFIG-SERVICE is temporarily disabled due to stability issues
        version_source_label = ctk.CTkLabel(grid_frame, text="API Source:")
        version_source_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        # Force FP if CONFIG-SERVICE was previously selected (since it's now disabled)
        current_source = self.config_manager.config.get("default_version_source", "FP")
        if current_source == "CONFIG-SERVICE":
            current_source = "FP"
            self.config_manager.config["default_version_source"] = "FP"
            self.config_manager.save_config_silent()

        self.version_source_var = ctk.StringVar(value=current_source)
        version_source_dropdown = ctk.CTkOptionMenu(
            grid_frame,
            variable=self.version_source_var,
            values=["FP"],  # CONFIG-SERVICE temporarily disabled
            command=self.on_version_source_change,
            width=200,
            state="disabled"  # Disable dropdown since only one option available
        )
        version_source_dropdown.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.create_tooltip(version_source_label, "API source for fetching default versions (CONFIG-SERVICE temporarily disabled)")
        self.create_tooltip(version_source_dropdown, "FP = Function Pack (FP/FPD scope)\n\nNOTE: CONFIG-SERVICE is temporarily disabled due to instability.\nOnly Function Pack API is available.")
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
            if (self.version_override_var and
                self.version_override_var.get() and
                self.pos_version_entry):

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
        """Test the API to fetch default versions"""
        self.api_client.test_default_versions_api()
