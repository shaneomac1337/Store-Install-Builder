import customtkinter as ctk
from config import ConfigManager
from generator import ProjectGenerator
import os
import tkinter.ttk as ttk
import sys
from tkinter import messagebox
import sys
import os

# Add parent directory to path to import PleasantPasswordClient
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pleasant_password_client import PleasantPasswordClient

class GKInstallBuilder:
    # Class variables to store KeePass client and credentials
    keepass_client = None
    keepass_username = None
    keepass_password = None
    
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("GK Install Builder")
        self.window.geometry("1200x900")  # Increased from 1000x800
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.config_manager = ConfigManager()
        self.project_generator = ProjectGenerator(parent_window=self.window)
        
        # Initialize password visibility tracking dictionary
        self.password_visible = {}
        
        # Track whether this is first run (no config file)
        self.is_first_run = not os.path.exists(self.config_manager.config_file)
        
        # Ensure default values are set for critical fields
        # ALWAYS set base_install_dir regardless of whether it's first run or not
        self.config_manager.config["base_install_dir"] = "C:\\gkretail"
        print("Setting default base install directory to C:\\gkretail in __init__")
        
        # Store section frames for progressive disclosure
        self.section_frames = {}
        
        # Create the GUI
        self.create_gui()
        
        # Auto-fill based on URL if available
        base_url = self.config_manager.config.get("base_url", "")
        if base_url:
            print(f"Initial base URL from config: {base_url}")
            self.auto_fill_based_on_url(base_url)
        
        # Set up window close handler
        self.window.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
    def create_gui(self):
        # Create main container with scrollbar
        self.main_frame = ctk.CTkScrollableFrame(self.window, width=900, height=700)
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Project Configuration
        self.create_section("Project Configuration", [
            "Project Name",
            "Base URL",
            "Version"
        ])
        
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
            self.create_section("Installation Configuration", [
                "Base Install Directory",
                "Tenant ID",
                "POS System Type",
                "WDM System Type",
                "Flow Service System Type",
                "LPA Service System Type",
                "StoreHub Service System Type",
                "Firebird Server Path"
            ])
            
            # Ensure base install directory is set
            base_dir_entry = self.config_manager.get_entry("base_install_dir")
            if base_dir_entry:
                current_value = base_dir_entry.get()
                if not current_value:
                    base_dir_entry.delete(0, 'end')
                    base_dir_entry.insert(0, "C:\\gkretail")
                    print("Set base install directory to C:\\gkretail in create_remaining_sections")
        
        # Security Configuration
        if "Security Configuration" not in self.section_frames:
            self.create_section("Security Configuration", [
                "EH/Launchpad Username",
                "EH/Launchpad Password",
                "Auth Service BA User",
                "Launchpad oAuth2",
                "SSL Password"
            ])
        
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
                    value = "C:\\gkretail"
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
        self.config_manager.config["base_install_dir"] = "C:\\gkretail"
        print("Setting default base install directory to C:\\gkretail in on_continue")
        
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
    
    def auto_fill_based_on_url(self, base_url):
        """Auto-fill fields based on the base URL"""
        print(f"\nAuto-filling based on URL: {base_url}")
        
        # Extract domain parts
        if "." in base_url:
            parts = base_url.split(".")
            
            # Extract environment and project name
            env_name = parts[0].upper() if parts[0] else "GKR"  # Default to GKR if empty
            
            # Extract project name from second part of domain (if available)
            project_name = "GKR"  # Default project name
            if len(parts) >= 2 and parts[1]:
                project_name = parts[1].upper()
            
            print(f"Extracted project name: {project_name}")
            
            # Determine system types based on project name
            pos_type = f"{project_name}-OPOS-CLOUD"
            wdm_type = f"{project_name}-wdm"
            lpa_type = f"{project_name}-lps-lpa"
            storehub_type = f"{project_name}-sh-cloud"
            # Flow Service typically remains GKR-based but can be overridden if needed
            flow_service_type = "GKR-FLOWSERVICE-CLOUD"
            
            print(f"Setting POS system type to: {pos_type}")
            print(f"Setting WDM system type to: {wdm_type}")
            print(f"Setting LPA Service system type to: {lpa_type}")
            print(f"Setting StoreHub Service system type to: {storehub_type}")
            print(f"Setting Flow Service system type to: {flow_service_type}")
            
            # ALWAYS update system types using the new method
            self.config_manager.update_entry_value("pos_system_type", pos_type)
            self.config_manager.update_entry_value("wdm_system_type", wdm_type)
            self.config_manager.update_entry_value("lpa_service_system_type", lpa_type)
            self.config_manager.update_entry_value("storehub_service_system_type", storehub_type)
            self.config_manager.update_entry_value("flow_service_system_type", flow_service_type)
            
            # ALWAYS update base install directory
            self.config_manager.update_entry_value("base_install_dir", "C:\\gkretail")
            print("Setting base install directory to: C:\\gkretail")
            
            # Update output directory based on project name and base URL
            # Create a structured output path: {project_name}/{base_url}
            output_dir = os.path.join(project_name, base_url)
            self.config_manager.update_entry_value("output_dir", output_dir)
            print(f"Setting output directory to: {output_dir}")
            
            # Update the output directory entry if it exists
            output_dir_entry = self.config_manager.get_entry("output_dir")
            if output_dir_entry:
                # For read-only entry, we need to enable it temporarily
                output_dir_entry.configure(state="normal")
                output_dir_entry.delete(0, 'end')
                output_dir_entry.insert(0, output_dir)
                output_dir_entry.configure(state="readonly")
                print(f"Updated output directory entry to: {output_dir}")
            
            # Update certificate path to be inside the output directory
            # Use the actual output directory instead of a fixed path
            certificate_path = os.path.join(output_dir, "certificate.p12")
            self.config_manager.update_entry_value("certificate_path", certificate_path)
            print(f"Setting certificate path to: {certificate_path}")
            
            # ALWAYS update certificate common name
            self.config_manager.update_entry_value("certificate_common_name", "*gk-software.com")
            
            # Set default values for other fields only if they're empty
            if self.config_manager.get_entry("tenant_id") and not self.config_manager.get_entry("tenant_id").get():
                self.config_manager.update_entry_value("tenant_id", "001")
            
            if self.config_manager.get_entry("username") and not self.config_manager.get_entry("username").get():
                self.config_manager.update_entry_value("username", "launchpad")
            
            if self.config_manager.get_entry("form_username") and not self.config_manager.get_entry("form_username").get():
                self.config_manager.update_entry_value("form_username", "1001")
            
            if self.config_manager.get_entry("ssl_password") and not self.config_manager.get_entry("ssl_password").get():
                self.config_manager.update_entry_value("ssl_password", "changeit")
        else:
            # Even if there's no valid URL, still set the base install directory
            self.config_manager.update_entry_value("base_install_dir", "C:\\gkretail")
            print("Setting base install directory to: C:\\gkretail (no valid URL provided)")
    
    def create_section(self, title, fields):
        # Section Frame
        section_frame = ctk.CTkFrame(self.main_frame)
        section_frame.pack(fill="x", padx=10, pady=(0, 20))
        
        # Store reference to section frame
        self.section_frames[title] = section_frame
        
        # Title
        ctk.CTkLabel(
            section_frame,
            text=title,
            font=("Helvetica", 16, "bold")
        ).pack(anchor="w", padx=10, pady=10)
        
        # Field tooltips - descriptions of what each field is for
        tooltips = {
            "Project Name": "Name of your store project (e.g., 'Coop Sweden')",
            "Base URL": "Base URL for the cloud retail environment (e.g., 'test.cse.cloud4retail.co')",
            "Version": "Version number of the installation (e.g., 'v1.2.0')",
            "Base Install Directory": "Root directory where components will be installed (e.g., 'C:\\gkretail')",
            "Tenant ID": "Tenant identifier for multi-tenant environments (e.g., '001')",
            "POS System Type": "Type of Point of Sale system (e.g., 'CSE-OPOS-CLOUD')",
            "WDM System Type": "Type of Workforce Management system (e.g., 'CSE-wdm')",
            "SSL Password": "Password for SSL certificate (default: 'changeit')",
            "Auth Service BA User": "Username for Auth-Service (e.g., 'launchpad'). If you don't know what you are doing, please keep launchpad",
            "EH/Launchpad Username": "Username for Employee Hub / Launchpad (e.g., '1001')",
            "Launchpad oAuth2": "Launchpad Auth Service password (click 🔑 to retrieve from KeePass)",
            "EH/Launchpad Password": "Employee Hub / Launchpad Password",
            "Firebird Server Path": "Path to the Firebird server (e.g., 'C:\\firebird\\server')",
        }
        
        # Fields
        for field in fields:
            field_frame = ctk.CTkFrame(section_frame)
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
            # Map the new field names to their config keys
            elif field == "EH/Launchpad Username":
                config_key = "form_username"
            elif field == "Launchpad oAuth2":
                config_key = "basic_auth_password"
            elif field == "EH/Launchpad Password":
                config_key = "form_password"
            # Map Auth Service BA User to username config key
            elif field == "Auth Service BA User":
                config_key = "username"
            else:
                config_key = field.lower().replace(" ", "_")
            
            # Check if this is a password field
            is_password_field = "password" in field.lower() or field == "Launchpad oAuth2"
            
            if is_password_field:
                # Create password field with show/hide toggle
                entry, toggle_btn = self.create_password_field(field_frame, field, config_key)
            else:
                # Create regular entry
                entry = ctk.CTkEntry(field_frame, width=400)
                entry.pack(side="left", padx=10)
                
                # Also add tooltip to the entry
                if field in tooltips:
                    self.create_tooltip(entry, tooltips[field])
                
                # Load saved value if exists
                if config_key in self.config_manager.config:
                    entry.insert(0, self.config_manager.config[config_key])
            
            self.config_manager.register_entry(config_key, entry)
            
            # Add KeePass button only for Launchpad oAuth2 field
            if field == "Launchpad oAuth2":
                self.basic_auth_password_entry = entry  # Store reference to this entry
                ctk.CTkButton(
                    field_frame,
                    text="🔑",  # Key icon
                    width=40,
                    command=self.get_basic_auth_password_from_keepass
                ).pack(side="left", padx=5)
            elif field == "EH/Launchpad Password":
                self.form_password_entry = entry  # Store reference to this entry
                # No KeePass button for Form Password
            elif field == "SSL Password":
                self.ssl_password_entry = entry  # Store reference to this entry
        
        # Add certificate management section if this is the Security Configuration section
        if title == "Security Configuration":
            self.create_certificate_section(section_frame)
            
            # Update certificate common name
            common_name_entry = self.config_manager.get_entry("certificate_common_name")
            if common_name_entry:
                common_name_entry.delete(0, 'end')
                common_name_entry.insert(0, "*gk-software.com")
                print("Updated certificate common name to: *gk-software.com")
            
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
        # Create the password entry with show=* for masking
        entry = ctk.CTkEntry(parent_frame, width=400, show="*")
        entry.pack(side="left", padx=10)
        
        # Load saved value if exists
        if config_key in self.config_manager.config:
            entry.insert(0, self.config_manager.config[config_key])
        
        # Initialize visibility state for this field
        self.password_visible[field] = False
        
        # Create toggle button that appears inside the entry field
        toggle_btn = ctk.CTkButton(
            parent_frame,
            text="👁️",  # Eye icon
            width=25,
            height=25,
            corner_radius=0,
            fg_color="transparent",
            hover_color="#CCCCCC",
            command=lambda e=entry, f=field: self.toggle_password_visibility(e, f)
        )
        
        # Position the button at the right side of the entry field
        toggle_btn.place(in_=entry, relx=0.95, rely=0.5, anchor="e")
        
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
        
        self.cert_path_entry = ctk.CTkEntry(cert_path_frame, width=300)
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
        
        self.cert_common_name_entry = ctk.CTkEntry(cert_common_name_frame, width=300)
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
            
            # Generate certificate using cryptography
            try:
                from cryptography import x509
                from cryptography.x509.oid import NameOID
                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import rsa
                import datetime
                
                # Generate private key
                key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048
                )
                
                # Create certificate subject
                subject = issuer = x509.Name([
                    x509.NameAttribute(NameOID.COUNTRY_NAME, "DE"),
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Saxony"),
                    x509.NameAttribute(NameOID.LOCALITY_NAME, "Dresden"),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "GK Software SE"),
                    x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                ])
                
                # Create certificate with SAN
                cert = x509.CertificateBuilder().subject_name(
                    subject
                ).issuer_name(
                    issuer
                ).public_key(
                    key.public_key()
                ).serial_number(
                    x509.random_serial_number()
                ).not_valid_before(
                    datetime.datetime.utcnow()
                ).not_valid_after(
                    # Valid for 10 years
                    datetime.datetime.utcnow() + datetime.timedelta(days=3650)
                ).add_extension(
                    x509.SubjectAlternativeName([x509.DNSName(common_name)]),
                    critical=False
                ).sign(key, hashes.SHA256())
                
                # Store certificate and key in memory instead of writing to files
                cert_pem = cert.public_bytes(serialization.Encoding.PEM)
                key_pem = key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
                # Try to convert to PKCS12 format
                try:
                    from cryptography.hazmat.primitives.serialization import pkcs12
                    
                    # Create PKCS12
                    p12 = pkcs12.serialize_key_and_certificates(
                        name=common_name.encode(),
                        key=key,
                        cert=cert,
                        cas=None,
                        encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
                    )
                    
                    # Write PKCS12 to file
                    with open(cert_path, "wb") as f:
                        f.write(p12)
                    
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
                    
                except (ImportError, AttributeError, Exception) as e2:
                    # If PKCS12 conversion fails, save the P12 using OpenSSL
                    import subprocess
                    import tempfile
                    
                    # Create temporary files for the cert and key
                    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_cert:
                        temp_cert.write(cert_pem)
                        temp_cert_path = temp_cert.name
                    
                    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_key:
                        temp_key.write(key_pem)
                        temp_key_path = temp_key.name
                    
                    try:
                        # Convert to PKCS12 using OpenSSL
                        subprocess.run(
                            f'openssl pkcs12 -export -out "{cert_path}" -inkey "{temp_key_path}" -in "{temp_cert_path}" -password pass:{password}',
                            shell=True, check=True
                        )
                        
                        # Show success message
                        self.cert_status_label.configure(text="Certificate generated", text_color="green")
                        self.show_info("Certificate Generated", 
                                      f"Certificate generated successfully at:\n{cert_path}\n\n"
                                      f"Common Name: {common_name}\n"
                                      f"Subject Alternative Name (SAN): {common_name}\n"
                                      f"Valid for: 10 years")
                    except Exception as e3:
                        self.cert_status_label.configure(text="Certificate generation failed", text_color="red")
                        self.show_error("Certificate Generation Failed", f"Error: {str(e3)}")
                    finally:
                        # Clean up temporary files
                        try:
                            os.unlink(temp_cert_path)
                            os.unlink(temp_key_path)
                        except:
                            pass
                    
                    # Update certificate status
                    self.check_certificate_status()
                    
                    return True
            except Exception as e1:
                # If cryptography fails, try OpenSSL directly
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
        
        # Get project version from config
        project_version = self.config_manager.config.get("version", "")
        
        # POS Version
        pos_label = ctk.CTkLabel(grid_frame, text="POS Version:")
        pos_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.pos_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.pos_version_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.pos_version_entry.insert(0, self.config_manager.config.get("pos_version", project_version))
        self.config_manager.register_entry("pos_version", self.pos_version_entry)
        self.create_tooltip(pos_label, "Version for POS components (applies to all POS system types)")
        self.create_tooltip(self.pos_version_entry, "Example: v1.0.0")
        
        # WDM Version
        wdm_label = ctk.CTkLabel(grid_frame, text="WDM Version:")
        wdm_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.wdm_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.wdm_version_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.wdm_version_entry.insert(0, self.config_manager.config.get("wdm_version", project_version))
        self.config_manager.register_entry("wdm_version", self.wdm_version_entry)
        self.create_tooltip(wdm_label, "Version for WDM components (applies to all WDM system types)")
        self.create_tooltip(self.wdm_version_entry, "Example: v1.0.0")
        
        # Flow Service Version
        flow_service_label = ctk.CTkLabel(grid_frame, text="Flow Service Version:")
        flow_service_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.flow_service_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.flow_service_version_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        self.flow_service_version_entry.insert(0, self.config_manager.config.get("flow_service_version", project_version))
        self.config_manager.register_entry("flow_service_version", self.flow_service_version_entry)
        self.create_tooltip(flow_service_label, "Version for Flow Service components")
        self.create_tooltip(self.flow_service_version_entry, "Example: v1.0.0")
        
        # LPA Service Version
        lpa_service_label = ctk.CTkLabel(grid_frame, text="LPA Service Version:")
        lpa_service_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.lpa_service_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.lpa_service_version_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.lpa_service_version_entry.insert(0, self.config_manager.config.get("lpa_service_version", project_version))
        self.config_manager.register_entry("lpa_service_version", self.lpa_service_version_entry)
        self.create_tooltip(lpa_service_label, "Version for LPA Service components")
        self.create_tooltip(self.lpa_service_version_entry, "Example: v1.0.0")
        
        # StoreHub Service Version
        storehub_service_label = ctk.CTkLabel(grid_frame, text="StoreHub Service Version:")
        storehub_service_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.storehub_service_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.storehub_service_version_entry.grid(row=5, column=1, padx=10, pady=5, sticky="w")
        self.storehub_service_version_entry.insert(0, self.config_manager.config.get("storehub_service_version", project_version))
        self.config_manager.register_entry("storehub_service_version", self.storehub_service_version_entry)
        self.create_tooltip(storehub_service_label, "Version for StoreHub Service components")
        self.create_tooltip(self.storehub_service_version_entry, "Example: v1.0.0")
        
        # Register the override checkbox with config manager
        self.config_manager.register_entry("use_version_override", self.version_override_var)
        
        # Initialize state based on config
        self.toggle_version_override()
    
    def toggle_version_override(self):
        """Toggle the enabled state of version fields based on checkbox"""
        enabled = self.version_override_var.get()
        state = "normal" if enabled else "disabled"
        
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
        
        # Entry with tooltip - make it read-only
        self.output_dir_entry = ctk.CTkEntry(frame, width=400, state="readonly")
        self.output_dir_entry.pack(side="left", padx=10)
        self.output_dir_entry.insert(0, self.config_manager.config["output_dir"])
        
        # Create tooltip for the entry
        self.create_tooltip(self.output_dir_entry, "Directory where generated installation files will be saved (automatically set based on Project Name and Base URL)")
        
        self.config_manager.register_entry("output_dir", self.output_dir_entry)
    
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
        """Create action buttons"""
        # Create frame for buttons
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # Generate button
        self.generate_button = ctk.CTkButton(
            button_frame,
            text="Generate Install Scripts",
            command=lambda: self.project_generator.generate(self.config_manager.config)
        )
        self.generate_button.pack(side="left", padx=10)
        
        # Offline Package Creator button
        self.offline_package_button = ctk.CTkButton(
            button_frame,
            text="Offline Package Creator",
            command=self.open_offline_package_creator
        )
        self.offline_package_button.pack(side="left", padx=10)
        
        # Create a frame for the KeePass button
        self.keepass_btn_frame = ctk.CTkFrame(button_frame)
        self.keepass_btn_frame.pack(side="left", padx=10)
        
        # Update the KeePass button state
        self.update_keepass_button()
    
    def update_keepass_button(self):
        """Update the KeePass credentials button based on current state"""
        # Clear any existing widgets in the frame
        for widget in self.keepass_btn_frame.winfo_children():
            widget.destroy()
            
        # Only create the button if KeePass client exists
        if hasattr(GKInstallBuilder, 'keepass_client') and GKInstallBuilder.keepass_client:
            self.clear_keepass_button = ctk.CTkButton(
                self.keepass_btn_frame,
                text="Clear KeePass Credentials",
                command=self.clear_keepass_credentials
            )
            self.clear_keepass_button.pack(side="left", padx=10)
    
    def on_window_close(self):
        """Handle window close event"""
        # Clear KeePass credentials
        GKInstallBuilder.keepass_client = None
        GKInstallBuilder.keepass_username = None
        GKInstallBuilder.keepass_password = None
        
        # Ensure all configuration is saved before exit
        try:
            # Clean up any lingering references to child windows
            if hasattr(self, 'offline_creator'):
                if hasattr(self.offline_creator, 'window') and self.offline_creator.window.winfo_exists():
                    self.offline_creator.window.destroy()
                delattr(self, 'offline_creator')
            
            # First, create a list of valid entries
            valid_entries = {}
            invalid_keys = []
            
            for key, entry in list(self.config_manager.entries.items()):
                try:
                    # Check if the entry widget still exists
                    if hasattr(entry, 'winfo_exists'):
                        try:
                            if entry.winfo_exists():
                                valid_entries[key] = entry
                            else:
                                invalid_keys.append(key)
                        except Exception:
                            # If checking existence fails, mark as invalid
                            invalid_keys.append(key)
                    else:
                        # If it's not a widget with winfo_exists, keep it
                        valid_entries[key] = entry
                except Exception:
                    # If there's any error, mark as invalid
                    invalid_keys.append(key)
            
            # Unregister all invalid entries
            for key in invalid_keys:
                try:
                    self.config_manager.unregister_entry(key)
                except Exception:
                    pass
            
            # Final safety check - remove any entries with "offline_creator" in the key
            for key in list(self.config_manager.entries.keys()):
                if "offline_creator" in key:
                    try:
                        self.config_manager.unregister_entry(key)
                    except Exception:
                        pass
            
            # Update config from all remaining entries
            self.config_manager.update_config_from_entries()
            
            # Save configuration
            if self.config_manager.save_config_silent():
                # If save was successful, destroy the window
                self.window.destroy()
            else:
                # If save failed, ask user if they want to exit anyway
                if messagebox.askyesno("Save Failed", 
                                      "Failed to save configuration. Exit anyway?"):
                    self.window.destroy()
        except Exception as e:
            # If an error occurred, show error and ask if user wants to exit anyway
            if messagebox.askyesno("Error", 
                                  f"An error occurred while saving: {str(e)}\nExit anyway?"):
                self.window.destroy()
    
    def open_offline_package_creator(self):
        """Open the Offline Package Creator window"""
        # Create a new toplevel window
        self.offline_creator = OfflinePackageCreator(
            parent=self.window,
            config_manager=self.config_manager,
            project_generator=self.project_generator,
            parent_app=self  # Pass the GKInstallBuilder instance
        )
        
        # Set up a callback for when the window is closed
        def cleanup_offline_creator():
            if hasattr(self, 'offline_creator'):
                delattr(self, 'offline_creator')
        
        # Add callback to be executed when the window is destroyed
        self.offline_creator.window.bind("<Destroy>", lambda e: cleanup_offline_creator())
    
    def create_webdav_browser(self):
        # Create WebDAV browser frame
        webdav_frame = ctk.CTkFrame(self.main_frame)
        webdav_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Title
        title_label = ctk.CTkLabel(
            webdav_frame,
            text="WebDAV Browser",
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Description
        description = ctk.CTkLabel(
            webdav_frame,
            text="Browse and download files from the WebDAV server.\n"
                 "Connect to the server using your credentials and navigate to the desired files.",
            justify="left"
        )
        description.pack(anchor="w", padx=10, pady=(0, 5))
        
        # Current path
        self.path_label = ctk.CTkLabel(webdav_frame, text="Current Path: /SoftwarePackage")
        self.path_label.pack(anchor="w", padx=10, pady=5)
        
        # Authentication frame
        auth_frame = ctk.CTkFrame(webdav_frame)
        auth_frame.pack(fill="x", padx=10, pady=5)
        
        # Username
        username_frame = ctk.CTkFrame(auth_frame)
        username_frame.pack(side="left", padx=5)
        username_label = ctk.CTkLabel(
            username_frame,
            text="Username:",
            width=100
        )
        username_label.pack(side="left")
        
        self.webdav_username = ctk.CTkEntry(username_frame, width=150)
        self.webdav_username.pack(side="left", padx=5)
        
        # Load saved username
        if self.config_manager.config["webdav_username"]:
            self.webdav_username.insert(0, self.config_manager.config["webdav_username"])
        
        # Register WebDAV username with config manager using a unique key for this window
        self.config_manager.register_entry("offline_creator_webdav_username", self.webdav_username)
        
        # Password
        password_frame = ctk.CTkFrame(auth_frame)
        password_frame.pack(side="left", padx=5)
        password_label = ctk.CTkLabel(
            password_frame,
            text="Password:",
            width=100
        )
        password_label.pack(side="left")
        
        self.webdav_password = ctk.CTkEntry(password_frame, width=150, show="*")
        self.webdav_password.pack(side="left", padx=5)
        
        # Load saved password
        if self.config_manager.config["webdav_password"]:
            self.webdav_password.insert(0, self.config_manager.config["webdav_password"])
            
        # Add KeePass button for WebDAV password
        ctk.CTkButton(
            password_frame,
            text="🔑",  # Key icon
            width=40,
            command=lambda: self.get_basic_auth_password_from_keepass(target_entry=self.webdav_password)
        ).pack(side="left", padx=5)
        
        # Register WebDAV password with config manager
        self.config_manager.register_entry("offline_creator_webdav_password", self.webdav_password)
            
        # Define a focus event handler to clear placeholder text
        def clear_placeholder(event):
            if self.webdav_password.get() == self.config_manager.config.get("webdav_password", ''):
                self.webdav_password.delete(0, 'end')

        # Define a focus out event handler to restore placeholder text
        def restore_placeholder(event):
            if self.webdav_password.get() == '':
                self.webdav_password.insert(0, self.config_manager.config.get("webdav_password", ''))

        # Bind the focus in and focus out events to the handlers
        self.webdav_password.bind('<FocusIn>', clear_placeholder)
        self.webdav_password.bind('<FocusOut>', restore_placeholder)
        
        # Connect button
        connect_btn = ctk.CTkButton(
            auth_frame,
            text="Connect",
            width=100,
            command=self.connect_webdav
        )
        connect_btn.pack(side="left", padx=10)
        
        # Status
        self.webdav_status = ctk.CTkLabel(
            auth_frame,
            text="Not Connected",
            text_color="red"
        )
        self.webdav_status.pack(side="left", padx=10)
        
        # Navigation buttons
        nav_frame = ctk.CTkFrame(webdav_frame)
        nav_frame.pack(fill="x", padx=10, pady=5)
        
        up_btn = ctk.CTkButton(
            nav_frame,
            text="Up",
            width=50,
            command=self.navigate_up
        )
        up_btn.pack(side="left", padx=5)
        
        refresh_btn = ctk.CTkButton(
            nav_frame,
            text="Refresh",
            width=70,
            command=self.refresh_listing
        )
        refresh_btn.pack(side="left", padx=5)
        
        # Directory listing - increase height and make it expand to fill available space
        self.dir_listbox = ctk.CTkScrollableFrame(webdav_frame, height=400)
        self.dir_listbox.pack(fill="both", expand=True, padx=10, pady=10)
    
    def connect_webdav(self):
        """Handle WebDAV connection"""
        base_url = self.config_manager.config["base_url"]
        username = self.webdav_username.get()
        password = self.webdav_password.get()
        
        if not all([base_url, username]):
            self.webdav_status.configure(
                text="Error: Base URL and username are required",
                text_color="red"
            )
            return
            
        # If password is the placeholder text, try to get it from KeePass
        if password == self.config_manager.config.get("webdav_password", '') and "Enter" in password:
            # Show a message that we're using the same password as basic auth
            self.webdav_status.configure(
                text="Using KeePass to get password...",
                text_color="orange"
            )
            self.window.update()
            
            # Try to use the same password as basic auth if it's available
            basic_auth_password = self.basic_auth_password_entry.get()
            if basic_auth_password and "Enter" not in basic_auth_password:
                password = basic_auth_password
                self.webdav_password.delete(0, 'end')
                self.webdav_password.insert(0, password)
        
        if not password:
            self.webdav_status.configure(
                text="Error: Password is required",
                text_color="red"
            )
            return
        
        # No need to manually update config as the entries are registered for auto-save
        
        self.webdav = self.project_generator.create_webdav_browser(
            base_url,
            username,
            password
        )
        
        success, message = self.webdav.connect()
        
        if success:
            self.webdav_status.configure(text="Connected", text_color="green")
            # Navigate to SoftwarePackage after successful connection
            self.webdav.current_path = "/SoftwarePackage"
            self.refresh_listing()
        else:
            self.webdav_status.configure(text=f"Connection failed: {message}", text_color="red")
    
    def refresh_listing(self):
        """Refresh the current directory listing"""
        try:
            # Clear existing items
            for widget in self.dir_listbox.winfo_children():
                widget.destroy()
            
            # Get all items
            items = self.webdav.list_directories(self.webdav.current_path)
            
            # Update path label
            self.path_label.configure(text=f"Current Path: {self.webdav.current_path}")
            
            # Sort items - directories first, then files
            items.sort(key=lambda x: (not x['is_directory'], x['name'].lower()))
            
            # Add buttons for directories and files
            for item in items:
                icon = "📁" if item['is_directory'] else "📄"
                btn = ctk.CTkButton(
                    self.dir_listbox,
                    text=f"{icon} {item['name']}",
                    anchor="w",
                    command=lambda d=item['name'], is_dir=item['is_directory']: 
                        self.handle_item_click(d, is_dir)
                )
                btn.pack(fill="x", padx=5, pady=2)
        
        except Exception as e:
            self.webdav_status.configure(text=f"Error: {str(e)}", text_color="red")
    
    def handle_item_click(self, name, is_directory):
        """Handle clicking on an item"""
        if is_directory:
            self.enter_directory(name)
    
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
    
    def create_offline_package(self):
        """Create offline package with selected components"""
        try:
            # Check if at least one component is selected
            if not (self.include_pos.get() or 
                   self.include_wdm.get() or 
                   self.include_flow_service.get() or 
                   self.include_lpa_service.get() or 
                   self.include_storehub_service.get()):
                self.show_error("Error", "Please select at least one component")
                return
            
            # Get selected components and their dependencies
            selected_components = []
            component_dependencies = {}
            
            if self.include_pos.get():
                selected_components.append("POS")
                component_dependencies["POS"] = self.pos_dependencies_needed.get()
                
            if self.include_wdm.get():
                selected_components.append("WDM")
                component_dependencies["WDM"] = self.wdm_dependencies_needed.get()
            
            if self.include_flow_service.get():
                selected_components.append("FLOW-SERVICE")
                component_dependencies["FLOW-SERVICE"] = self.flow_service_dependencies_needed.get()
                
            if self.include_lpa_service.get():
                selected_components.append("LPA-SERVICE")
                component_dependencies["LPA-SERVICE"] = self.lpa_service_dependencies_needed.get()
                
            if self.include_storehub_service.get():
                selected_components.append("STOREHUB-SERVICE")
                component_dependencies["STOREHUB-SERVICE"] = self.storehub_service_dependencies_needed.get()
            
            # Update config with component dependencies
            self.config_manager.config["component_dependencies"] = component_dependencies
            
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

    def get_basic_auth_password_from_keepass(self, target_entry=None):
        """Open a dialog to get Launchpad oAuth2 Password from KeePass"""
        # If no target entry is specified, use the basic auth password entry
        if target_entry is None:
            target_entry = self.basic_auth_password_entry
            
        # Create a toplevel window
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("KeePass Authentication")
        dialog.geometry("500x550")  # Increased from 450x400
        dialog.transient(self.window)
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
        env_combo = ctk.CTkComboBox(env_frame, width=200, variable=env_var, values=["TEST", "PROD"])
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
        
        # Define on_search_change function early so it can be referenced before its definition
        def on_search_change(*args):
            update_project_list()
            
        # Function to connect to KeePass
        def connect_to_keepass():
            try:
                status_var.set("Connecting to KeePass...")
                
                # Create a new client
                client = PleasantPasswordClient(
                    base_url="https://keeserver.gk.gk-software.com/api/v5/rest/",
                    username=username_var.get(),
                    password=password_var.get()
                )
                
                # If remember checkbox is checked, save the credentials
                if remember_var.get():
                    GKInstallBuilder.keepass_client = client
                    GKInstallBuilder.keepass_username = username_var.get()
                    GKInstallBuilder.keepass_password = password_var.get()
                    
                    # Update the KeePass button state in the main window
                    self.update_keepass_button()
                
                # Store client for later use
                dialog.client = client
                
                # Update status
                status_var.set("Connected to KeePass! Auto-detecting environment...")
                
                # Run auto-detection immediately
                connect()
                
                # If we successfully connected and detected environment, get_password_btn will be enabled
                # by the connect() function
                
            except Exception as e:
                status_var.set(f"Connection error: {str(e)}")
                
        # Function to detect available projects
        def detect_projects():
            try:
                client = dialog.client
                
                # Get project folder
                projects_folder_id = "87300a24-9741-4d24-8a5c-a8b04e0b7049"
                folder_structure = client.get_folder(projects_folder_id)
                
                # Get all project folders
                projects = self.get_subfolders(folder_structure)
                
                if not projects:
                    status_var.set("No projects found!")
                    return
                
                # Create a project selection dialog
                project_dialog = ctk.CTkToplevel(dialog)
                project_dialog.title("Select Project")
                project_dialog.geometry("400x600")  # Increased from 300x450
                project_dialog.transient(dialog)
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
                
                # Function to update project list based on filter
                def update_project_list():
                    # Clear existing buttons
                    for widget in projects_frame.winfo_children():
                        widget.destroy()
                    
                    # Get filter text
                    filter_text = filter_var.get().lower()
                    
                    # Add filtered projects
                    for project in dialog.all_projects:
                        project_name = project['name']
                        if filter_text in project_name.lower():
                            project_btn = ctk.CTkButton(
                                projects_frame,
                                text=project_name,
                                command=lambda p=project: select_project(p)
                            )
                            project_btn.pack(fill="x", pady=2)
                
                # Function to select a project
                def select_project(project):
                    # Get the project ID if it's not already set
                    project_id = project['id']
                    if project_id is None:
                        # Find the ID from folder structure
                        project_id = self.find_folder_id_by_name(folder_structure, project['name'])
                        if not project_id:
                            status_var.set(f"Could not find folder ID for {project['name']}")
                            return
                        project['id'] = project_id
                    
                    # Now get environments for this project
                    folder_id = project_id
                    folder_contents = client.get_folder(folder_id)
                    subfolders = self.get_subfolders(folder_contents)
                    
                    # Update environment dropdown with actual values from the project
                    env_values = [folder['name'] for folder in subfolders] if isinstance(subfolders[0], dict) else subfolders
                    env_combo.configure(values=env_values)
                    if env_values:
                        env_var.set(env_values[0])  # Set first environment as default
                    
                    # Store folder contents for later use
                    dialog.folder_contents = folder_contents
                    
                    # Close the project dialog
                    project_dialog.destroy()
                    
                    # Update the dialog state with the selected project
                    dialog.selected_project = project['name']
                    
                    # Enable get password button
                    get_password_btn.configure(state="normal")
                    
                    # Update status
                    status_var.set(f"Selected project: {project['name']}")
                
                # Add trace after defining the function
                filter_var.trace_add("write", on_search_change)
                
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
                
                # Get project folder
                projects_folder_id = "87300a24-9741-4d24-8a5c-a8b04e0b7049"
                folder_structure = client.get_folder(projects_folder_id)
                
                # Try to determine project name AND environment from the base URL automatically
                project_name = "AZR-CSE"  # Default project
                detected_env = "TEST"  # Default environment
                
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
                
                folder_id = self.find_folder_id_by_name(folder_structure, project_name)
                
                if not folder_id:
                    status_var.set(f"Folder '{project_name}' not found! Click 'Detect Projects' to choose manually.")
                    detect_projects_btn.configure(state="normal")
                    return
                
                # Get environments for this project
                folder_contents = client.get_folder(folder_id)
                subfolders = self.get_subfolders(folder_contents)
                
                # Update environment dropdown with actual values from the project
                env_values = [folder['name'] for folder in subfolders] if isinstance(subfolders[0], dict) else subfolders
                env_combo.configure(values=env_values)
                
                # Check if our detected environment exists in the available environments
                detected_env_exists = False
                for env in env_values:
                    if env == detected_env:  # Exact match only
                        detected_env_exists = True
                        break
                
                # Set the environment value
                if env_values:
                    if detected_env_exists:
                        env_var.set(detected_env)  # Set our detected environment if it exists
                        print(f"Setting detected environment: {detected_env}")
                    else:
                        env_var.set(env_values[0])  # Otherwise use the first available environment
                        print(f"Detected environment '{detected_env}' not found, using: {env_values[0]}")
                
                # Store folder contents for later use
                dialog.folder_contents = folder_contents
                
                # Store project name for later use
                dialog.selected_project = project_name
                
                # Store folder structure for recursive search
                dialog.folder_structure = folder_structure
                
                # Update status with Environment Autodetect message
                status_var.set(f"Environment Autodetect - {project_name}")
                
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
                    connect()
                    if not hasattr(dialog, 'selected_project'):
                        status_var.set("No project selected! Click 'Detect Projects' to select a project.")
                        return
                
                project_name = dialog.selected_project
                environment = env_var.get()
                
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
                        
                        # Find the credential in this environment
                        entry = self.find_basic_auth_password_entry(env_structure)
                        
                        if entry:
                            # Get the password
                            if isinstance(entry, dict) and 'Id' in entry:
                                try:
                                    # Direct API call to get the password
                                    password_url = f"credentials/{entry['Id']}/password"
                                    print(f"Making API call to: {password_url}")
                                    password = client._make_request('GET', password_url)
                                    # Set password in the target entry field
                                    target_entry.delete(0, 'end')
                                    target_entry.insert(0, str(password).strip())
                                    status_var.set(f"Retrieved credential successfully!")
                                except Exception as e:
                                    status_var.set(f"Error retrieving password: {str(e)}")
                                    print(f"Error getting password: {str(e)}")
                            # For backwards compatibility, try to access password as attribute
                            elif hasattr(entry, 'password'):
                                password = entry.password
                                target_entry.delete(0, 'end')
                                target_entry.insert(0, password)
                                status_var.set(f"Retrieved credential successfully!")
                            else:
                                status_var.set(f"Error: Unsupported entry format")
                                print(f"Unsupported entry format: {type(entry)}")
                                
                            # Close the dialog after successful retrieval
                            dialog.after(2000, on_dialog_close)
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
                    
                    # In that environment, now we need to find the credentials
                    entry = self.find_basic_auth_password_entry(env_folder)
                    
                    if entry:
                        # Get the password - entry might be a dict, not an object with a password attribute
                        if isinstance(entry, dict) and 'Id' in entry:
                            try:
                                # Direct API call to get the password
                                password_url = f"credentials/{entry['Id']}/password"
                                print(f"Making API call to: {password_url}")
                                password = client._make_request('GET', password_url)
                                # Set password in the target entry field
                                target_entry.delete(0, 'end')
                                target_entry.insert(0, str(password).strip())
                                status_var.set(f"Retrieved credential successfully!")
                            except Exception as e:
                                status_var.set(f"Error retrieving password: {str(e)}")
                                print(f"Error getting password: {str(e)}")
                        # For backwards compatibility, try to access password as attribute
                        elif hasattr(entry, 'password'):
                            password = entry.password
                            target_entry.delete(0, 'end')
                            target_entry.insert(0, password)
                            status_var.set(f"Retrieved credential successfully!")
                        else:
                            status_var.set(f"Error: Unsupported entry format")
                            print(f"Unsupported entry format: {type(entry)}")
                        
                        # Close the dialog after 2 seconds
                        dialog.after(2000, on_dialog_close)
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
                
                # Dynamically build the target credential name based on environment
                if env_name:
                    target_cred_name = f"{env_name}-LAUNCHPAD-OAUTH-BA-PASSWORD"
                    
                    # First priority: exact match for {ENV}-LAUNCHPAD-OAUTH-BA-PASSWORD in APP subfolder
                    if cred_name == target_cred_name and "APP" in current_path:
                        print(f"FOUND TARGET ENTRY: {target_cred_name} in {current_path}")
                        target_entry = cred
                        return cred
                    
                    # Second priority: exact match for {ENV}-LAUNCHPAD-OAUTH-BA-PASSWORD anywhere
                    if cred_name == target_cred_name:
                        print(f"FOUND EXACT MATCH: {target_cred_name} in {current_path}")
                        found_entries.append({
                            'priority': 1,
                            'entry': cred,
                            'path': current_path,
                            'reason': f'Exact match for {target_cred_name}'
                        })
            
            # Third priority: entries with LAUNCHPAD-OAUTH-BA-PASSWORD
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'LAUNCHPAD-OAUTH-BA-PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains LAUNCHPAD-OAUTH-BA-PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 2,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains LAUNCHPAD-OAUTH-BA-PASSWORD: {cred_name}'
                    })
            
            # Fourth priority: entries with BA-PASSWORD
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'BA-PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains BA-PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 3,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains BA-PASSWORD: {cred_name}'
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
            print(f"\nNo exact match for {env_name}-LAUNCHPAD-OAUTH-BA-PASSWORD found in APP subfolder.")
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
            tooltip_window = ctk.CTkToplevel(self.window)
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
        self.window.bind("<Destroy>", lambda e: leave(e), add="+")

    def run(self):
        self.window.mainloop()

    def clear_keepass_credentials(self):
        """Clear saved KeePass credentials"""
        GKInstallBuilder.keepass_client = None
        GKInstallBuilder.keepass_username = None
        GKInstallBuilder.keepass_password = None
        
        # Update the KeePass button state
        if hasattr(self, 'update_keepass_button'):
            self.update_keepass_button()
            
        messagebox.showinfo("KeePass Credentials", "KeePass credentials have been cleared.")

# New class for the Offline Package Creator window
class OfflinePackageCreator:
    def __init__(self, parent, config_manager, project_generator, parent_app=None):
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Offline Package Creator")
        self.window.geometry("1200x900")  # Increased from 1000x800
        self.window.transient(parent)  # Set to be on top of the parent window
        
        # Add window close protocol handler
        self.window.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
        # Store references
        self.config_manager = config_manager
        self.project_generator = project_generator
        self.parent_app = parent_app  # Store reference to the parent application (GKInstallBuilder instance)
        
        # Create main frame with scrollbar
        self.main_frame = ctk.CTkScrollableFrame(self.window)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create WebDAV browser
        self.create_webdav_browser()
        
        # Create offline package section
        self.create_offline_package_section()
        
    def on_window_close(self):
        """Handle window close event"""
        try:
            # Force update of config from entries before unregistering them
            self.config_manager.update_config_from_entries()
            
            # Explicitly handle the webdav entries
            if hasattr(self, 'webdav_username'):
                try:
                    # Save the value to the main config key
                    if hasattr(self.webdav_username, 'get'):
                        self.config_manager.config["webdav_username"] = self.webdav_username.get()
                    
                    # Unregister the entry
                    if "webdav_username" in self.config_manager.entries:
                        self.config_manager.unregister_entry("webdav_username")
                    if "offline_creator_webdav_username" in self.config_manager.entries:
                        self.config_manager.unregister_entry("offline_creator_webdav_username")
                except Exception:
                    pass
            
            if hasattr(self, 'webdav_password'):
                try:
                    # Save the value to the main config key
                    if hasattr(self.webdav_password, 'get'):
                        self.config_manager.config["webdav_password"] = self.webdav_password.get()
                    
                    # Unregister the entry
                    if "webdav_password" in self.config_manager.entries:
                        self.config_manager.unregister_entry("webdav_password")
                    if "offline_creator_webdav_password" in self.config_manager.entries:
                        self.config_manager.unregister_entry("offline_creator_webdav_password")
                except Exception:
                    pass
            
            # Get a copy of all entry keys
            all_keys = list(self.config_manager.entries.keys())
            
            # Unregister all entries - this is a more aggressive approach
            # but ensures no lingering references remain
            for key in all_keys:
                try:
                    self.config_manager.unregister_entry(key)
                except Exception:
                    pass
                    
            # Save the configuration silently
            self.config_manager.save_config_silent()
        except Exception:
            # Ignore any errors during cleanup
            pass
        finally:
            # Always destroy the window
            self.window.destroy()
    
    def create_offline_package_section(self):
        # Create frame for offline package options
        self.offline_package_frame = ctk.CTkFrame(self.window)
        self.offline_package_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Title
        ctk.CTkLabel(
            self.offline_package_frame, 
            text="Create Offline Package",
            font=("Helvetica", 16, "bold")
        ).pack(pady=(10, 5), padx=10)
        
        # Description
        ctk.CTkLabel(
            self.offline_package_frame, 
            text="Select components to include in the offline package:",
            font=("Helvetica", 12)
        ).pack(pady=(0, 10), padx=10)
        
        # Components frame
        self.components_frame = ctk.CTkFrame(self.offline_package_frame)
        self.components_frame.pack(fill="x", padx=10, pady=5)
        
        # POS component frame
        pos_component_frame = ctk.CTkFrame(self.components_frame)
        pos_component_frame.pack(fill="x", pady=5, padx=10)
        
        # POS checkbox
        self.include_pos = ctk.BooleanVar(value=True)
        pos_checkbox = ctk.CTkCheckBox(
            pos_component_frame,
            text="POS",
            variable=self.include_pos,
            checkbox_width=20,
            checkbox_height=20
        )
        pos_checkbox.pack(side="left", pady=5, padx=10)
        
        # POS dependencies checkbox
        self.pos_dependencies_needed = ctk.BooleanVar(value=False)
        pos_dependencies_checkbox = ctk.CTkCheckBox(
            pos_component_frame,
            text="Include Java & Tomcat",
            variable=self.pos_dependencies_needed,
            checkbox_width=20,
            checkbox_height=20
        )
        pos_dependencies_checkbox.pack(side="left", pady=5, padx=20)
        
        # WDM component frame
        wdm_component_frame = ctk.CTkFrame(self.components_frame)
        wdm_component_frame.pack(fill="x", pady=5, padx=10)
        
        # WDM checkbox
        self.include_wdm = ctk.BooleanVar(value=True)
        wdm_checkbox = ctk.CTkCheckBox(
            wdm_component_frame,
            text="WDM",
            variable=self.include_wdm,
            checkbox_width=20,
            checkbox_height=20
        )
        wdm_checkbox.pack(side="left", pady=5, padx=10)
        
        # WDM dependencies checkbox
        self.wdm_dependencies_needed = ctk.BooleanVar(value=False)
        wdm_dependencies_checkbox = ctk.CTkCheckBox(
            wdm_component_frame,
            text="Include Java & Tomcat",
            variable=self.wdm_dependencies_needed,
            checkbox_width=20,
            checkbox_height=20
        )
        wdm_dependencies_checkbox.pack(side="left", pady=5, padx=20)
        
        # Flow Service component frame
        flow_service_component_frame = ctk.CTkFrame(self.components_frame)
        flow_service_component_frame.pack(fill="x", pady=5, padx=10)
        
        # Flow Service checkbox
        self.include_flow_service = ctk.BooleanVar(value=False)
        flow_service_checkbox = ctk.CTkCheckBox(
            flow_service_component_frame,
            text="Flow Service",
            variable=self.include_flow_service,
            checkbox_width=20,
            checkbox_height=20
        )
        flow_service_checkbox.pack(side="left", pady=5, padx=10)
        
        # Flow Service dependencies checkbox
        self.flow_service_dependencies_needed = ctk.BooleanVar(value=False)
        flow_service_dependencies_checkbox = ctk.CTkCheckBox(
            flow_service_component_frame,
            text="Include Java & Tomcat",
            variable=self.flow_service_dependencies_needed,
            checkbox_width=20,
            checkbox_height=20
        )
        flow_service_dependencies_checkbox.pack(side="left", pady=5, padx=20)
        
        # LPA Service component frame
        lpa_service_component_frame = ctk.CTkFrame(self.components_frame)
        lpa_service_component_frame.pack(fill="x", pady=5, padx=10)
        
        # LPA Service checkbox
        self.include_lpa_service = ctk.BooleanVar(value=False)
        lpa_service_checkbox = ctk.CTkCheckBox(
            lpa_service_component_frame,
            text="LPA Service",
            variable=self.include_lpa_service,
            checkbox_width=20,
            checkbox_height=20
        )
        lpa_service_checkbox.pack(side="left", pady=5, padx=10)
        
        # LPA Service dependencies checkbox
        self.lpa_service_dependencies_needed = ctk.BooleanVar(value=False)
        lpa_service_dependencies_checkbox = ctk.CTkCheckBox(
            lpa_service_component_frame,
            text="Include Java & Tomcat",
            variable=self.lpa_service_dependencies_needed,
            checkbox_width=20,
            checkbox_height=20
        )
        lpa_service_dependencies_checkbox.pack(side="left", pady=5, padx=20)
        
        # StoreHub Service component frame
        storehub_service_component_frame = ctk.CTkFrame(self.components_frame)
        storehub_service_component_frame.pack(fill="x", pady=5, padx=10)
        
        # StoreHub Service checkbox
        self.include_storehub_service = ctk.BooleanVar(value=False)
        storehub_service_checkbox = ctk.CTkCheckBox(
            storehub_service_component_frame,
            text="StoreHub Service",
            variable=self.include_storehub_service,
            checkbox_width=20,
            checkbox_height=20
        )
        storehub_service_checkbox.pack(side="left", pady=5, padx=10)
        
        # StoreHub Service dependencies checkbox
        self.storehub_service_dependencies_needed = ctk.BooleanVar(value=False)
        storehub_service_dependencies_checkbox = ctk.CTkCheckBox(
            storehub_service_component_frame,
            text="Include Java & Tomcat",
            variable=self.storehub_service_dependencies_needed,
            checkbox_width=20,
            checkbox_height=20
        )
        storehub_service_dependencies_checkbox.pack(side="left", pady=5, padx=20)
        
        # Create button
        self.create_button = ctk.CTkButton(
            self.offline_package_frame,
            text="Create Offline Package",
            command=self.create_offline_package
        )
        self.create_button.pack(pady=10, padx=10)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.offline_package_frame,
            text="",
            font=("Helvetica", 12)
        )
        self.status_label.pack(pady=5, padx=10)
    
    def create_webdav_browser(self):
        # Create WebDAV browser frame
        webdav_frame = ctk.CTkFrame(self.main_frame)
        webdav_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Title
        title_label = ctk.CTkLabel(
            webdav_frame,
            text="WebDAV Browser",
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Description
        description = ctk.CTkLabel(
            webdav_frame,
            text="Browse and download files from the WebDAV server.\n"
                 "Connect to the server using your credentials and navigate to the desired files.",
            justify="left"
        )
        description.pack(anchor="w", padx=10, pady=(0, 5))
        
        # Current path
        self.path_label = ctk.CTkLabel(webdav_frame, text="Current Path: /SoftwarePackage")
        self.path_label.pack(anchor="w", padx=10, pady=5)
        
        # Authentication frame
        auth_frame = ctk.CTkFrame(webdav_frame)
        auth_frame.pack(fill="x", padx=10, pady=5)
        
        # Username
        username_frame = ctk.CTkFrame(auth_frame)
        username_frame.pack(side="left", padx=5)
        username_label = ctk.CTkLabel(
            username_frame,
            text="Username:",
            width=100
        )
        username_label.pack(side="left")
        
        self.webdav_username = ctk.CTkEntry(username_frame, width=150)
        self.webdav_username.pack(side="left", padx=5)
        
        # Load saved username
        if self.config_manager.config["webdav_username"]:
            self.webdav_username.insert(0, self.config_manager.config["webdav_username"])
        
        # Register WebDAV username with config manager using a unique key for this window
        self.config_manager.register_entry("offline_creator_webdav_username", self.webdav_username)
        
        # Password
        password_frame = ctk.CTkFrame(auth_frame)
        password_frame.pack(side="left", padx=5)
        password_label = ctk.CTkLabel(
            password_frame,
            text="Password:",
            width=100
        )
        password_label.pack(side="left")
        
        self.webdav_password = ctk.CTkEntry(password_frame, width=150, show="*")
        self.webdav_password.pack(side="left", padx=5)
        
        # Load saved password
        if self.config_manager.config["webdav_password"]:
            self.webdav_password.insert(0, self.config_manager.config["webdav_password"])
            
        # Add KeePass button for WebDAV password
        ctk.CTkButton(
            password_frame,
            text="🔑",  # Key icon
            width=40,
            command=lambda: self.get_basic_auth_password_from_keepass(target_entry=self.webdav_password)
        ).pack(side="left", padx=5)
        
        # Register WebDAV password with config manager
        self.config_manager.register_entry("offline_creator_webdav_password", self.webdav_password)
            
        # Define a focus event handler to clear placeholder text
        def clear_placeholder(event):
            if self.webdav_password.get() == self.config_manager.config.get("webdav_password", ''):
                self.webdav_password.delete(0, 'end')

        # Define a focus out event handler to restore placeholder text
        def restore_placeholder(event):
            if self.webdav_password.get() == '':
                self.webdav_password.insert(0, self.config_manager.config.get("webdav_password", ''))

        # Bind the focus in and focus out events to the handlers
        self.webdav_password.bind('<FocusIn>', clear_placeholder)
        self.webdav_password.bind('<FocusOut>', restore_placeholder)
        
        # Connect button
        connect_btn = ctk.CTkButton(
            auth_frame,
            text="Connect",
            width=100,
            command=self.connect_webdav
        )
        connect_btn.pack(side="left", padx=10)
        
        # Status
        self.webdav_status = ctk.CTkLabel(
            auth_frame,
            text="Not Connected",
            text_color="red"
        )
        self.webdav_status.pack(side="left", padx=10)
        
        # Navigation buttons
        nav_frame = ctk.CTkFrame(webdav_frame)
        nav_frame.pack(fill="x", padx=10, pady=5)
        
        up_btn = ctk.CTkButton(
            nav_frame,
            text="Up",
            width=50,
            command=self.navigate_up
        )
        up_btn.pack(side="left", padx=5)
        
        refresh_btn = ctk.CTkButton(
            nav_frame,
            text="Refresh",
            width=70,
            command=self.refresh_listing
        )
        refresh_btn.pack(side="left", padx=5)
        
        # Directory listing - increase height and make it expand to fill available space
        self.dir_listbox = ctk.CTkScrollableFrame(webdav_frame, height=400)
        self.dir_listbox.pack(fill="both", expand=True, padx=10, pady=10)
    
    def connect_webdav(self):
        """Handle WebDAV connection"""
        base_url = self.config_manager.config["base_url"]
        username = self.webdav_username.get()
        password = self.webdav_password.get()
        
        if not all([base_url, username]):
            self.webdav_status.configure(
                text="Error: Base URL and username are required",
                text_color="red"
            )
            return
            
        # If password is the placeholder text, try to get it from KeePass
        if password == self.config_manager.config.get("webdav_password", '') and "Enter" in password:
            # Show a message that we're using the same password as basic auth
            self.webdav_status.configure(
                text="Using KeePass to get password...",
                text_color="orange"
            )
            self.window.update()
            
            # Try to use the same password as basic auth if it's available
            basic_auth_password = self.basic_auth_password_entry.get()
            if basic_auth_password and "Enter" not in basic_auth_password:
                password = basic_auth_password
                self.webdav_password.delete(0, 'end')
                self.webdav_password.insert(0, password)
        
        if not password:
            self.webdav_status.configure(
                text="Error: Password is required",
                text_color="red"
            )
            return
        
        # No need to manually update config as the entries are registered for auto-save
        
        self.webdav = self.project_generator.create_webdav_browser(
            base_url,
            username,
            password
        )
        
        success, message = self.webdav.connect()
        
        if success:
            self.webdav_status.configure(text="Connected", text_color="green")
            # Navigate to SoftwarePackage after successful connection
            self.webdav.current_path = "/SoftwarePackage"
            self.refresh_listing()
        else:
            self.webdav_status.configure(text=f"Connection failed: {message}", text_color="red")
    
    def refresh_listing(self):
        """Refresh the current directory listing"""
        try:
            # Clear existing items
            for widget in self.dir_listbox.winfo_children():
                widget.destroy()
            
            # Get all items
            items = self.webdav.list_directories(self.webdav.current_path)
            
            # Update path label
            self.path_label.configure(text=f"Current Path: {self.webdav.current_path}")
            
            # Sort items - directories first, then files
            items.sort(key=lambda x: (not x['is_directory'], x['name'].lower()))
            
            # Add buttons for directories and files
            for item in items:
                icon = "📁" if item['is_directory'] else "📄"
                btn = ctk.CTkButton(
                    self.dir_listbox,
                    text=f"{icon} {item['name']}",
                    anchor="w",
                    command=lambda d=item['name'], is_dir=item['is_directory']: 
                        self.handle_item_click(d, is_dir)
                )
                btn.pack(fill="x", padx=5, pady=2)
        
        except Exception as e:
            self.webdav_status.configure(text=f"Error: {str(e)}", text_color="red")
    
    def handle_item_click(self, name, is_directory):
        """Handle clicking on an item"""
        if is_directory:
            self.enter_directory(name)
    
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
    
    def create_offline_package(self):
        """Create offline package with selected components"""
        try:
            # Check if at least one component is selected
            if not (self.include_pos.get() or 
                   self.include_wdm.get() or 
                   self.include_flow_service.get() or 
                   self.include_lpa_service.get() or 
                   self.include_storehub_service.get()):
                self.show_error("Error", "Please select at least one component")
                return
            
            # Get selected components and their dependencies
            selected_components = []
            component_dependencies = {}
            
            if self.include_pos.get():
                selected_components.append("POS")
                component_dependencies["POS"] = self.pos_dependencies_needed.get()
                
            if self.include_wdm.get():
                selected_components.append("WDM")
                component_dependencies["WDM"] = self.wdm_dependencies_needed.get()
            
            if self.include_flow_service.get():
                selected_components.append("FLOW-SERVICE")
                component_dependencies["FLOW-SERVICE"] = self.flow_service_dependencies_needed.get()
                
            if self.include_lpa_service.get():
                selected_components.append("LPA-SERVICE")
                component_dependencies["LPA-SERVICE"] = self.lpa_service_dependencies_needed.get()
                
            if self.include_storehub_service.get():
                selected_components.append("STOREHUB-SERVICE")
                component_dependencies["STOREHUB-SERVICE"] = self.storehub_service_dependencies_needed.get()
            
            # Update config with component dependencies
            self.config_manager.config["component_dependencies"] = component_dependencies
            
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

    def get_basic_auth_password_from_keepass(self, target_entry=None):
        """Delegate to the parent app's get_basic_auth_password_from_keepass method"""
        # Use the stored reference to the parent app (GKInstallBuilder instance)
        if self.parent_app and hasattr(self.parent_app, 'get_basic_auth_password_from_keepass'):
            self.parent_app.get_basic_auth_password_from_keepass(target_entry=target_entry)
        else:
            # Show an error if the parent app doesn't have the method
            messagebox.showerror("Error", "Could not access KeePass integration from parent application.")

def main():
    app = GKInstallBuilder()
    app.run()

if __name__ == "__main__":
    main() 