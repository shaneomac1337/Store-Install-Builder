"""
Detection Settings Dialog for Store-Install-Builder
Provides configuration for hostname detection, file detection, and environment detection
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog

# Import UI helpers
try:
    from gk_install_builder.ui.helpers import bind_mousewheel_to_frame
    from gk_install_builder.utils.tooltips import create_tooltip
except ImportError:
    from ui.helpers import bind_mousewheel_to_frame
    from utils.tooltips import create_tooltip


class DetectionSettingsDialog:
    """Dialog for configuring detection settings"""

    def __init__(self, parent, config_manager, detection_manager, hostname_detection_var, detection_var, parent_app=None):
        """
        Initialize Detection Settings Dialog

        Args:
            parent: Parent window
            config_manager: ConfigManager instance
            detection_manager: DetectionManager instance
            hostname_detection_var: BooleanVar for hostname detection checkbox
            detection_var: BooleanVar for file detection checkbox
            parent_app: Reference to parent GKInstallBuilder instance
        """
        self.parent = parent
        self.config_manager = config_manager
        self.detection_manager = detection_manager
        self.hostname_detection_var = hostname_detection_var
        self.detection_var = detection_var
        self.parent_app = parent_app

        # Initialize window reference
        self.window = None

        # Initialize instance variables for UI elements
        self.path_approach_var = None
        self.base_dir_entry = None
        self.filename_entries = {}
        self.file_path_entries = {}
        self.windows_regex_entry = None
        self.linux_regex_entry = None
        self.windows_test_entry = None
        self.linux_test_entry = None
        self.windows_results_text = None
        self.linux_results_text = None
        self.hostname_env_detection_var = None
        self.env_group_dropdown = None
        self.store_group_dropdown = None
        self.workstation_group_dropdown = None

    def show(self):
        """Show the detection settings dialog"""
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        # Create a new window for detection settings
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("Detection Settings")
        self.window.geometry("1024x1024")
        self.window.transient(self.parent)

        # Force window update and wait for it to be visible before grabbing
        self.window.update()

        # Add a short delay to ensure the window is fully mapped on Linux
        self.window.after(100, lambda: self._safe_grab_set(self.window))

        # Main frame with scrollbar
        main_frame = ctk.CTkScrollableFrame(self.window)
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

        # Build each tab
        self._build_environment_tab(tab_environment)
        self._build_file_detection_tab(tab_file_detection)
        self._build_hostname_tab(tab_regex)

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
            command=self.window.destroy
        )
        cancel_btn.pack(side="right", padx=10)

    def _build_environment_tab(self, tab):
        """Build the environment detection tab"""
        # ----- ENVIRONMENT DETECTION TAB -----

        ctk.CTkLabel(
            tab,
            text="Multi-Environment Auto-Detection",
            font=("Helvetica", 14, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            tab,
            text="Installation scripts automatically detect the correct environment (P, DEV, Q-001, etc.) for multi-tenant deployments.",
            wraplength=650
        ).pack(anchor="w", padx=10, pady=(0, 10))

        # Environment count
        environments = self.config_manager.get_environments()
        env_count = len(environments)

        count_frame = ctk.CTkFrame(tab)
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
                command=self._open_environment_manager,
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
        priority_frame = ctk.CTkFrame(tab)
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
        env_format_frame = ctk.CTkFrame(tab)
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

    def _build_file_detection_tab(self, tab):
        """Build the file detection tab"""
        # ----- FILE DETECTION TAB -----

        ctk.CTkLabel(
            tab,
            text="Configure file-based detection to extract store IDs and workstation IDs from station files.",
            wraplength=650
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            tab,
            text="File detection is used as a fallback when hostname detection fails or is disabled.",
            wraplength=650,
            text_color="gray70",
        ).pack(anchor="w", padx=10, pady=(0, 10))

        # Enable/disable detection checkbox
        enable_frame = ctk.CTkFrame(tab)
        enable_frame.pack(fill="x", padx=10, pady=5)

        # Create checkbox for detection
        detection_checkbox = ctk.CTkCheckBox(
            enable_frame,
            text="Enable file-based detection",
            variable=self.detection_var,
            onvalue=True,
            offvalue=False
        )
        detection_checkbox.pack(anchor="w", padx=10, pady=10)

        # Add an explanatory label for the current settings
        hostname_detection_enabled = self.hostname_detection_var.get()

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
        format_frame = ctk.CTkFrame(tab)
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

        # Path approach selection
        ctk.CTkLabel(
            tab,
            text="Path Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(15, 5))
        approach_frame = ctk.CTkFrame(tab)
        approach_frame.pack(fill="x", padx=10, pady=5)

        self.path_approach_var = ctk.StringVar(
            value="base_dir" if self.detection_manager.is_using_base_directory() else "custom_paths"
        )

        ctk.CTkRadioButton(
            approach_frame,
            text="Use base directory with standard file names",
            variable=self.path_approach_var,
            value="base_dir",
            command=self.update_detection_ui
        ).pack(anchor="w", padx=10, pady=5)

        ctk.CTkRadioButton(
            approach_frame,
            text="Use custom file paths for each component",
            variable=self.path_approach_var,
            value="custom_paths",
            command=self.update_detection_ui
        ).pack(anchor="w", padx=10, pady=5)

        # Base directory approach frame
        ctk.CTkLabel(
            tab,
            text="Base Directory Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(15, 5))

        self.base_dir_frame = ctk.CTkFrame(tab)
        self.base_dir_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Base Directory
        base_dir_label_frame = ctk.CTkFrame(self.base_dir_frame, fg_color="transparent")
        base_dir_label_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            base_dir_label_frame,
            text="Base Directory:",
            width=120,
            anchor="w"
        ).pack(side="left")

        self.base_dir_entry = ctk.CTkEntry(base_dir_label_frame, width=500)
        self.base_dir_entry.pack(side="left", padx=(0, 10))

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

        # Register with config manager so PlatformHandler can update it when platform changes
        self.config_manager.register_entry("file_detection_base_directory", self.base_dir_entry)

        ctk.CTkButton(
            base_dir_label_frame,
            text="Browse",
            width=80,
            command=self.browse_base_directory
        ).pack(side="left")

        # Filenames configuration
        filenames_frame = ctk.CTkFrame(self.base_dir_frame)
        filenames_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            filenames_frame,
            text="Customize Station File Names (optional):",
            font=("Helvetica", 11)
        ).pack(anchor="w", padx=10, pady=5)

        # Create filename entries for each component
        components = ["POS", "ONEX-POS", "WDM", "FLOW-SERVICE", "LPA-SERVICE", "STOREHUB-SERVICE"]
        for component in components:
            row_frame = ctk.CTkFrame(filenames_frame)
            row_frame.pack(fill="x", padx=10, pady=2)

            ctk.CTkLabel(
                row_frame,
                text=f"{component}:",
                width=120
            ).pack(side="left", padx=10)

            entry = ctk.CTkEntry(row_frame, width=200)
            entry.pack(side="left", padx=10)
            entry.insert(0, self.detection_manager.get_custom_filename(component))
            self.filename_entries[component] = entry

        # Custom paths approach frame
        self.custom_paths_frame = ctk.CTkFrame(tab)
        self.custom_paths_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            self.custom_paths_frame,
            text="Custom Paths Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)

        # Create path entries for each component
        for component in components:
            row_frame = ctk.CTkFrame(self.custom_paths_frame)
            row_frame.pack(fill="x", padx=10, pady=5)

            ctk.CTkLabel(
                row_frame,
                text=f"{component}:",
                width=120
            ).pack(side="left", padx=10)

            entry = ctk.CTkEntry(row_frame, width=400)
            entry.pack(side="left", padx=10)
            entry.insert(0, self.detection_manager.get_file_path(component))
            self.file_path_entries[component] = entry

            ctk.CTkButton(
                row_frame,
                text="Browse",
                width=80,
                command=lambda c=component: self.browse_station_file(c)
            ).pack(side="left", padx=10)

        # Update visibility
        self.update_detection_ui()

    def _build_hostname_tab(self, tab_regex):
        """Build the hostname detection tab"""
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
        self.group_mapping_frame = ctk.CTkFrame(env_detection_frame)
        self.group_mapping_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(
            self.group_mapping_frame,
            text="Regex Group Mapping (Advanced):",
            font=("Helvetica", 11, "bold"),
            text_color="#FF8C00"
        ).pack(anchor="w", padx=10, pady=(5, 5))

        ctk.CTkLabel(
            self.group_mapping_frame,
            text="Configure which regex capture group corresponds to each value.",
            text_color="gray70",
            font=("Helvetica", 9),
            wraplength=650
        ).pack(anchor="w", padx=10, pady=(0, 5))

        # Get current group mappings
        group_mappings = self.detection_manager.get_all_group_mappings()

        # Create a sub-frame for the dropdowns
        dropdowns_frame = ctk.CTkFrame(self.group_mapping_frame, fg_color="transparent")
        dropdowns_frame.pack(fill="x", padx=20, pady=5)

        # Environment group dropdown
        self.env_group_frame = ctk.CTkFrame(dropdowns_frame, fg_color="transparent")
        self.env_group_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(
            self.env_group_frame,
            text="Environment:",
            width=120,
            anchor="w"
        ).pack(side="left", padx=(0, 10))

        self.env_group_dropdown = ctk.CTkOptionMenu(
            self.env_group_frame,
            values=["1", "2", "3"],
            width=80
        )
        self.env_group_dropdown.set(str(group_mappings["env"]))
        self.env_group_dropdown.pack(side="left")

        ctk.CTkLabel(
            self.env_group_frame,
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
            self.group_mapping_frame,
            text="Example: For hostname '1234-P-101' with regex '^([0-9]+)-([A-Z])-([0-9]+)$', set Environment=2, Store=1, Workstation=3",
            text_color="#4a9eff",
            font=("Helvetica", 9),
            wraplength=650,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(5, 5))

        # ----- REGEX EDITOR -----
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

        # Update UI to hide/show environment dropdown based on current setting
        self.update_detection_ui()

    def create_regex_editor(self, parent_frame, platform):
        """Create a regex editor section for a specific platform"""
        # Create a frame for this platform
        platform_frame = ctk.CTkFrame(parent_frame)
        platform_frame.pack(fill="x", padx=10, pady=10)

        # Title
        ctk.CTkLabel(
            platform_frame,
            text=f"{platform} Hostname Pattern",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Regex input
        regex_row = ctk.CTkFrame(platform_frame, fg_color="transparent")
        regex_row.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            regex_row,
            text="Regex Pattern:",
            width=120,
            anchor="w"
        ).pack(side="left", padx=(0, 10))

        regex_entry = ctk.CTkEntry(regex_row, width=600)
        regex_entry.pack(side="left", fill="x", expand=True)

        # Load current regex
        current_regex = self.detection_manager.get_hostname_regex(platform.lower())
        if current_regex:
            regex_entry.insert(0, current_regex)

        # Store the entry
        if platform == "Windows":
            self.windows_regex_entry = regex_entry
        else:
            self.linux_regex_entry = regex_entry

        # Test hostname input
        test_row = ctk.CTkFrame(platform_frame, fg_color="transparent")
        test_row.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            test_row,
            text="Test Hostname:",
            width=120,
            anchor="w"
        ).pack(side="left", padx=(0, 10))

        test_entry = ctk.CTkEntry(test_row, width=400)
        test_entry.pack(side="left", padx=(0, 10))

        # Load test hostname
        test_hostname = self.detection_manager.get_test_hostname()
        if test_hostname:
            test_entry.insert(0, test_hostname)

        # Store the entry
        if platform == "Windows":
            self.windows_test_entry = test_entry
        else:
            self.linux_test_entry = test_entry

        # Test button
        test_btn = ctk.CTkButton(
            test_row,
            text="Test Pattern",
            width=120,
            command=lambda p=platform: self.test_regex(p)
        )
        test_btn.pack(side="left")

        # Example
        ctk.CTkLabel(
            platform_frame,
            text=f"Example {platform} hostname: {'POS-P0001-002' if platform == 'Windows' else 'pos-p0001-002'}",
            font=("Helvetica", 10),
            text_color="#95A5A6"
        ).pack(anchor="w", padx=10, pady=(0, 10))

        # Results frame
        results_frame = ctk.CTkFrame(platform_frame)
        results_frame.pack(fill="x", padx=10, pady=5)

        # Create a text widget to show results
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
            if platform.lower() == "windows":
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

    def _open_environment_manager(self):
        """Open the environment manager from the detection settings dialog"""
        if self.parent_app and hasattr(self.parent_app, 'open_environment_manager'):
            self.parent_app.open_environment_manager()
        else:
            messagebox.showinfo(
                "Environment Manager",
                "Environment Manager can be opened from the main window."
            )

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
        """Update the detection UI based on current settings"""
        # Update file detection tab visibility
        if hasattr(self, 'path_approach_var') and self.path_approach_var is not None:
            is_base_dir = self.path_approach_var.get() == "base_dir"

            if is_base_dir:
                self.base_dir_frame.pack(fill="both", expand=True, padx=10, pady=10)
                self.custom_paths_frame.pack_forget()
            else:
                self.base_dir_frame.pack_forget()
                self.custom_paths_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Update environment detection tab visibility
        if (hasattr(self, 'hostname_env_detection_var') and self.hostname_env_detection_var is not None and
            hasattr(self, 'env_group_frame') and self.env_group_frame is not None):
            if self.hostname_env_detection_var.get():
                # Show environment dropdown for 3-group mode
                self.env_group_frame.pack(fill="x", pady=2)
            else:
                # Hide environment dropdown for 2-group mode
                self.env_group_frame.pack_forget()

    def on_env_detection_toggle(self):
        """Handle environment detection toggle"""
        # Update the detection manager setting
        is_enabled = self.hostname_env_detection_var.get()
        self.detection_manager.set_hostname_env_detection(is_enabled)

        # Automatically apply the appropriate pattern template
        if is_enabled:
            # Enable 3-group pattern
            self.apply_3group_pattern_silent()
            messagebox.showinfo(
                "3-Group Pattern Enabled",
                "Environment detection from hostname has been enabled.\n\n"
                "The regex pattern has been updated to support 3-group detection:\n"
                "- Environment (e.g., P, D, T)\n"
                "- Store ID (e.g., 1234)\n"
                "- Workstation ID (e.g., 101)\n\n"
                "Example: P1234-101"
            )
        else:
            # Enable 2-group pattern
            self.apply_classic_2group_pattern_silent()
            messagebox.showinfo(
                "2-Group Pattern Enabled",
                "Environment detection from hostname has been disabled.\n\n"
                "The regex pattern has been updated to support 2-group detection:\n"
                "- Store ID (e.g., 1234)\n"
                "- Workstation ID (e.g., 101)\n\n"
                "Example: 1234-101"
            )

        # Update UI to show/hide environment dropdown
        self.update_detection_ui()

    def apply_3group_pattern_silent(self):
        """Apply the 3-group pattern template without showing messagebox"""
        # Set the detection manager to use 3-group pattern
        self.detection_manager.set_using_3group_pattern(True)

        # Set default 3-group regex patterns
        windows_pattern = r"^([A-Z]+)([0-9]{4})-([0-9]{3})$"
        linux_pattern = r"^([a-z]+)([0-9]{4})-([0-9]{3})$"

        if hasattr(self, 'windows_regex_entry'):
            self.windows_regex_entry.delete(0, 'end')
            self.windows_regex_entry.insert(0, windows_pattern)

        if hasattr(self, 'linux_regex_entry'):
            self.linux_regex_entry.delete(0, 'end')
            self.linux_regex_entry.insert(0, linux_pattern)

        # Set test hostname
        if hasattr(self, 'windows_test_entry'):
            self.windows_test_entry.delete(0, 'end')
            self.windows_test_entry.insert(0, "P1234-101")

        if hasattr(self, 'linux_test_entry'):
            self.linux_test_entry.delete(0, 'end')
            self.linux_test_entry.insert(0, "p1234-101")

        # Set group mappings for 3-group pattern: Environment=1, Store ID=2, Workstation ID=3
        if hasattr(self, 'env_group_dropdown') and self.env_group_dropdown:
            self.env_group_dropdown.set("1")
            self.detection_manager.set_group_mapping('env', 1)

        if hasattr(self, 'store_group_dropdown') and self.store_group_dropdown:
            self.store_group_dropdown.set("2")
            self.detection_manager.set_group_mapping('store', 2)

        if hasattr(self, 'workstation_group_dropdown') and self.workstation_group_dropdown:
            self.workstation_group_dropdown.set("3")
            self.detection_manager.set_group_mapping('workstation', 3)

    def apply_classic_2group_pattern_silent(self):
        """Apply the classic 2-group pattern template without showing messagebox"""
        # Set the detection manager to use 2-group pattern
        self.detection_manager.set_using_3group_pattern(False)

        # Set default 2-group regex patterns
        windows_pattern = r"^([0-9]{4})-([0-9]{3})$"
        linux_pattern = r"^([0-9]{4})-([0-9]{3})$"

        if hasattr(self, 'windows_regex_entry'):
            self.windows_regex_entry.delete(0, 'end')
            self.windows_regex_entry.insert(0, windows_pattern)

        if hasattr(self, 'linux_regex_entry'):
            self.linux_regex_entry.delete(0, 'end')
            self.linux_regex_entry.insert(0, linux_pattern)

        # Set test hostname
        if hasattr(self, 'windows_test_entry'):
            self.windows_test_entry.delete(0, 'end')
            self.windows_test_entry.insert(0, "1234-101")

        if hasattr(self, 'linux_test_entry'):
            self.linux_test_entry.delete(0, 'end')
            self.linux_test_entry.insert(0, "1234-101")

        # Set group mappings for 2-group pattern: Store ID=1, Workstation ID=2
        if hasattr(self, 'store_group_dropdown') and self.store_group_dropdown:
            self.store_group_dropdown.set("1")
            self.detection_manager.set_group_mapping('store', 1)

        if hasattr(self, 'workstation_group_dropdown') and self.workstation_group_dropdown:
            self.workstation_group_dropdown.set("2")
            self.detection_manager.set_group_mapping('workstation', 2)

    def apply_3group_pattern(self):
        """Apply the 3-group pattern template"""
        # Set the detection manager to use 3-group pattern
        self.detection_manager.set_using_3group_pattern(True)

        # Set default 3-group regex patterns
        windows_pattern = r"POS-([A-Z]+)(\d{4})-(\d{3})"
        linux_pattern = r"pos-([a-z]+)(\d{4})-(\d{3})"

        if hasattr(self, 'windows_regex_entry'):
            self.windows_regex_entry.delete(0, 'end')
            self.windows_regex_entry.insert(0, windows_pattern)

        if hasattr(self, 'linux_regex_entry'):
            self.linux_regex_entry.delete(0, 'end')
            self.linux_regex_entry.insert(0, linux_pattern)

        # Set test hostname
        if hasattr(self, 'windows_test_entry'):
            self.windows_test_entry.delete(0, 'end')
            self.windows_test_entry.insert(0, "POS-P0001-002")

        if hasattr(self, 'linux_test_entry'):
            self.linux_test_entry.delete(0, 'end')
            self.linux_test_entry.insert(0, "pos-p0001-002")

        # Enable environment detection
        if hasattr(self, 'hostname_env_detection_var'):
            self.hostname_env_detection_var.set(True)

        # Update UI
        self.update_detection_ui()

        messagebox.showinfo(
            "Pattern Applied",
            "3-Group pattern template applied!\n\n"
            "Pattern format: <Prefix>-<Env><StoreID>-<WorkstationID>\n"
            "Example: POS-P0001-002\n\n"
            "Environment detection has been enabled.\n"
            "You can now test the pattern with your hostname."
        )

    def apply_classic_2group_pattern(self):
        """Apply the classic 2-group pattern template"""
        # Set the detection manager to use 2-group pattern
        self.detection_manager.set_using_3group_pattern(False)

        # Set default 2-group regex patterns
        windows_pattern = r"POS-(\d{4})-(\d{3})"
        linux_pattern = r"pos-(\d{4})-(\d{3})"

        if hasattr(self, 'windows_regex_entry'):
            self.windows_regex_entry.delete(0, 'end')
            self.windows_regex_entry.insert(0, windows_pattern)

        if hasattr(self, 'linux_regex_entry'):
            self.linux_regex_entry.delete(0, 'end')
            self.linux_regex_entry.insert(0, linux_pattern)

        # Set test hostname
        if hasattr(self, 'windows_test_entry'):
            self.windows_test_entry.delete(0, 'end')
            self.windows_test_entry.insert(0, "POS-0001-002")

        if hasattr(self, 'linux_test_entry'):
            self.linux_test_entry.delete(0, 'end')
            self.linux_test_entry.insert(0, "pos-0001-002")

        # Disable environment detection
        if hasattr(self, 'hostname_env_detection_var'):
            self.hostname_env_detection_var.set(False)

        # Update UI
        self.update_detection_ui()

        messagebox.showinfo(
            "Pattern Applied",
            "Classic 2-Group pattern template applied!\n\n"
            "Pattern format: <Prefix>-<StoreID>-<WorkstationID>\n"
            "Example: POS-0001-002\n\n"
            "Environment detection has been disabled.\n"
            "You can now test the pattern with your hostname."
        )

    def browse_base_directory(self):
        """Browse for base directory"""
        directory = filedialog.askdirectory(
            title="Select Base Directory for Station Files"
        )
        if directory:
            self.base_dir_entry.delete(0, 'end')
            self.base_dir_entry.insert(0, directory)

    def browse_station_file(self, component):
        """Browse for a station file"""
        filename = filedialog.askopenfilename(
            title=f"Select {component} Station File"
        )
        if filename:
            if component in self.file_path_entries:
                self.file_path_entries[component].delete(0, 'end')
                self.file_path_entries[component].insert(0, filename)

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
            base_dir = self.base_dir_entry.get()
            self.detection_manager.set_base_directory(base_dir)
            # Also update the main config to keep in sync with PlatformHandler
            self.config_manager.config["file_detection_base_directory"] = base_dir

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
        if self.window:
            self.window.destroy()

        messagebox.showinfo("Success", "Detection settings saved successfully.")
