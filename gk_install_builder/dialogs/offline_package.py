"""
Offline Package Creator Dialog for Store-Install-Builder
Provides DSG API browser and offline package creation functionality
"""

import customtkinter as ctk
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import os
import requests
import json
import traceback
import urllib3
import threading
import time

# Import UI helpers
from ui.helpers import bind_mousewheel_to_frame
from utils.tooltips import create_tooltip


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
        """Download a file to the output directory with progress dialog"""
        import os
        import requests
        from tkinter import messagebox
        import customtkinter as ctk
        import urllib3
        import threading

        # Suppress SSL warnings for faster downloads
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        try:
            # Get output directory from config (convert to absolute path)
            output_dir = self.config_manager.config.get("output_dir", "generated_scripts")
            download_dir = os.path.abspath(output_dir)

            # Create downloaded_packages subdirectory in output directory
            download_dir = os.path.join(download_dir, "downloaded_packages")
            os.makedirs(download_dir, exist_ok=True)

            # Build full remote path
            remote_path = f"{self._browser_state['current_path']}/{item['name']}".replace('//', '/')

            # Local file path in output directory's downloaded_packages folder
            local_path = os.path.join(download_dir, item['name'])

            print(f"\n=== Downloading File (Context Menu) ===")
            print(f"Output directory: {output_dir}")
            print(f"Download directory: {download_dir}")
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
            # Get relative path for display
            try:
                rel_path = os.path.relpath(local_path)
            except:
                rel_path = local_path

            self.status_label.configure(
                text=f"Downloaded {item['name']} to output directory",
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
