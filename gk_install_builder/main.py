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
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("GK Install Builder")
        self.window.geometry("1000x800")
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.config_manager = ConfigManager()
        self.project_generator = ProjectGenerator(parent_window=self.window)
        
        # Initialize password visibility tracking dictionary
        self.password_visible = {}
        
        # Track whether this is first run (no config file)
        self.is_first_run = not os.path.exists(self.config_manager.config_file)
        
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
                "WDM System Type"
            ])
        
        # Security Configuration
        if "Security Configuration" not in self.section_frames:
            self.create_section("Security Configuration", [
                "SSL Password",
                "Username",
                "Form Username",
                "Basic Auth Password",
                "Form Password"
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
            for key in ["pos_system_type", "wdm_system_type"]:
                value = self.config_manager.config.get(key, "")
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
        
        pos_entry = self.config_manager.get_entry("pos_system_type")
        wdm_entry = self.config_manager.get_entry("wdm_system_type")
        
        if pos_entry and pos_type:
            pos_entry.delete(0, 'end')
            pos_entry.insert(0, pos_type)
            print(f"Force updated POS system type to: {pos_type}")
            
        if wdm_entry and wdm_type:
            wdm_entry.delete(0, 'end')
            wdm_entry.insert(0, wdm_type)
            print(f"Force updated WDM system type to: {wdm_type}")
    
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
            
            print(f"Setting POS system type to: {pos_type}")
            print(f"Setting WDM system type to: {wdm_type}")
            
            # ALWAYS update POS and WDM system types using the new method
            self.config_manager.update_entry_value("pos_system_type", pos_type)
            self.config_manager.update_entry_value("wdm_system_type", wdm_type)
            
            # Set default values for other fields only if they're empty
            if self.config_manager.get_entry("base_install_dir") and not self.config_manager.get_entry("base_install_dir").get():
                self.config_manager.update_entry_value("base_install_dir", "C:\\gkretail")
            
            if self.config_manager.get_entry("tenant_id") and not self.config_manager.get_entry("tenant_id").get():
                self.config_manager.update_entry_value("tenant_id", "001")
            
            if self.config_manager.get_entry("username") and not self.config_manager.get_entry("username").get():
                self.config_manager.update_entry_value("username", "launchpad")
            
            if self.config_manager.get_entry("form_username") and not self.config_manager.get_entry("form_username").get():
                self.config_manager.update_entry_value("form_username", "1001")
            
            if self.config_manager.get_entry("ssl_password") and not self.config_manager.get_entry("ssl_password").get():
                self.config_manager.update_entry_value("ssl_password", "changeit")
    
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
            "Project Name": "Name of your store project (e.g., 'Store123 Installation')",
            "Base URL": "Base URL for the cloud retail environment (e.g., 'example.cloud4retail.co')",
            "Version": "Version number of the installation (e.g., 'v1.0.0')",
            "Base Install Directory": "Root directory where components will be installed (e.g., 'C:\\gkretail')",
            "Tenant ID": "Tenant identifier for multi-tenant environments (e.g., '001')",
            "POS System Type": "Type of Point of Sale system (e.g., 'GKR-OPOS-CLOUD')",
            "WDM System Type": "Type of Workforce Management system (e.g., 'CSE-wdm')",
            "SSL Password": "Password for SSL certificate (default: 'changeit')",
            "Username": "Username for authentication (e.g., 'launchpad')",
            "Form Username": "Username for form authentication (e.g., '1001')",
            "Basic Auth Password": "Password for basic authentication (click 🔑 to retrieve from KeePass)",
            "Form Password": "Password for form authentication"
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
            
            config_key = field.lower().replace(" ", "_")
            
            # Check if this is a password field
            is_password_field = "password" in field.lower()
            
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
            
            # Add KeePass button only for Basic Auth Password field
            if field == "Basic Auth Password":
                self.basic_auth_password_entry = entry  # Store reference to this entry
                ctk.CTkButton(
                    field_frame,
                    text="🔑",  # Key icon
                    width=40,
                    command=self.get_basic_auth_password_from_keepass
                ).pack(side="left", padx=5)
            elif field == "Form Password":
                self.form_password_entry = entry  # Store reference to this entry
                # No KeePass button for Form Password
            elif field == "SSL Password":
                self.ssl_password_entry = entry  # Store reference to this entry
        
        # Add certificate management section if this is the Security Configuration section
        if title == "Security Configuration":
            self.create_certificate_section(section_frame)
            
        # Special handling for Installation Configuration section
        if title == "Installation Configuration":
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
                    
                    if pos_entry:
                        pos_entry.delete(0, 'end')
                        pos_entry.insert(0, pos_type)
                        print(f"Updated POS system type to: {pos_type}")
                    
                    if wdm_entry:
                        wdm_entry.delete(0, 'end')
                        wdm_entry.insert(0, wdm_type)
                        print(f"Updated WDM system type to: {wdm_type}")
    
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
        """Create a section for SSL certificate management"""
        # Certificate frame
        cert_frame = ctk.CTkFrame(parent_frame)
        cert_frame.pack(fill="x", padx=10, pady=10)
        
        # Title
        cert_title = ctk.CTkLabel(
            cert_frame,
            text="SSL Certificate Management",
            font=("Helvetica", 14, "bold")
        )
        cert_title.pack(anchor="w", padx=10, pady=5)
        self.create_tooltip(cert_title, "Manage SSL certificates for secure connections")
        
        # Certificate info frame
        info_frame = ctk.CTkFrame(cert_frame)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        # Certificate status
        status_label = ctk.CTkLabel(
            info_frame,
            text="Certificate Status:",
            width=150
        )
        status_label.pack(side="left", padx=10)
        
        self.cert_status = ctk.CTkLabel(
            info_frame,
            text="No certificate generated",
            text_color="orange"
        )
        self.cert_status.pack(side="left", padx=10)
        
        # Certificate path frame
        path_frame = ctk.CTkFrame(cert_frame)
        path_frame.pack(fill="x", padx=10, pady=5)
        
        # Certificate path
        path_label = ctk.CTkLabel(
            path_frame,
            text="Certificate Path:",
            width=150
        )
        path_label.pack(side="left", padx=10)
        
        self.cert_path_entry = ctk.CTkEntry(path_frame, width=300)
        self.cert_path_entry.pack(side="left", padx=10)
        
        # Load saved certificate path
        if "certificate_path" in self.config_manager.config:
            self.cert_path_entry.insert(0, self.config_manager.config["certificate_path"])
        else:
            # Default to a path in the output directory
            default_path = os.path.join(self.config_manager.config["output_dir"], "cse_wdm.p12")
            self.cert_path_entry.insert(0, default_path)
        
        # Register with config manager
        self.config_manager.register_entry("certificate_path", self.cert_path_entry)
        
        # Browse button
        browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse",
            width=80,
            command=self.browse_certificate_path
        )
        browse_btn.pack(side="left", padx=5)
        
        # Certificate generation frame
        gen_frame = ctk.CTkFrame(cert_frame)
        gen_frame.pack(fill="x", padx=10, pady=5)
        
        # Common Name field
        cn_label = ctk.CTkLabel(
            gen_frame,
            text="Common Name:",
            width=150
        )
        cn_label.pack(side="left", padx=10)
        self.create_tooltip(cn_label, "Domain name for the certificate (e.g., 'store.example.com')")
        
        self.common_name_entry = ctk.CTkEntry(gen_frame, width=300)
        self.common_name_entry.pack(side="left", padx=10)
        self.common_name_entry.insert(0, "store.example.com")
        
        # Register with config manager
        self.config_manager.register_entry("certificate_common_name", self.common_name_entry)
        
        # Buttons frame
        btn_frame = ctk.CTkFrame(cert_frame)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        # Generate button
        generate_btn = ctk.CTkButton(
            btn_frame,
            text="Generate Certificate",
            width=150,
            command=self.generate_certificate
        )
        generate_btn.pack(side="left", padx=10)
        self.create_tooltip(generate_btn, "Generate a new self-signed SSL certificate")
        
        # View button
        view_btn = ctk.CTkButton(
            btn_frame,
            text="View Certificate",
            width=150,
            command=self.view_certificate
        )
        view_btn.pack(side="left", padx=10)
        self.create_tooltip(view_btn, "View details of the current certificate")
        
        # Check certificate status on startup
        self.check_certificate_status()
    
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
            self.cert_status.configure(text="Certificate exists", text_color="green")
        else:
            self.cert_status.configure(text="No certificate found", text_color="orange")
    
    def generate_certificate(self):
        """Generate a new self-signed certificate"""
        try:
            # Get certificate details
            cert_path = self.cert_path_entry.get()
            common_name = self.common_name_entry.get()
            password = self.ssl_password_entry.get() if hasattr(self, 'ssl_password_entry') else self.config_manager.config.get("ssl_password", "changeit")
            
            # Create directory if it doesn't exist
            cert_dir = os.path.dirname(cert_path)
            os.makedirs(cert_dir, exist_ok=True)
            
            # Generate a more descriptive filename based on common name
            if common_name:
                # Create a safe filename from common name
                safe_name = "".join(c if c.isalnum() else "_" for c in common_name)
                # Limit length and ensure it's not empty
                safe_name = safe_name[:30] or "certificate"
                
                # Update the certificate path with the new name
                cert_path = os.path.join(cert_dir, f"{safe_name}.p12")
                self.cert_path_entry.delete(0, 'end')
                self.cert_path_entry.insert(0, cert_path)
            
            # Try different methods to generate certificate
            try:
                # First try with cryptography library (most modern)
                from cryptography import x509
                from cryptography.x509.oid import NameOID
                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import rsa
                from datetime import datetime, timedelta
                import ipaddress
                
                # Generate private key
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                )
                
                # Create a self-signed certificate
                subject = issuer = x509.Name([
                    x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
                    x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Organization"),
                    x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Organizational Unit"),
                    x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                ])
                
                cert = x509.CertificateBuilder().subject_name(
                    subject
                ).issuer_name(
                    issuer
                ).public_key(
                    private_key.public_key()
                ).serial_number(
                    x509.random_serial_number()
                ).not_valid_before(
                    datetime.utcnow()
                ).not_valid_after(
                    datetime.utcnow() + timedelta(days=3650)  # 10 years
                ).add_extension(
                    x509.SubjectAlternativeName([x509.DNSName(common_name)]),
                    critical=False,
                ).sign(private_key, hashes.SHA256())
                
                # Write the certificate to a PEM file
                cert_file = cert_path.replace('.p12', '.crt')
                key_file = cert_path.replace('.p12', '.key')
                
                with open(cert_file, "wb") as f:
                    f.write(cert.public_bytes(serialization.Encoding.PEM))
                
                with open(key_file, "wb") as f:
                    f.write(private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
                
                # Create PKCS12 file
                try:
                    # Try to create PKCS12 using cryptography
                    from cryptography.hazmat.primitives.serialization.pkcs12 import serialize_key_and_certificates
                    
                    # Create PKCS12
                    pkcs12_data = serialize_key_and_certificates(
                        name=common_name.encode('utf-8'),
                        key=private_key,
                        cert=cert,
                        cas=None,
                        encryption_algorithm=serialization.BestAvailableEncryption(password.encode('utf-8'))
                    )
                    
                    # Write PKCS12 file
                    with open(cert_path, "wb") as f:
                        f.write(pkcs12_data)
                    
                    # Show success message
                    self.cert_status.configure(text="Certificate generated", text_color="green")
                    self.show_info("Certificate Generated", 
                                  f"Certificate generated successfully at:\n{cert_path}\n\n"
                                  f"PEM files also available at:\n{cert_file}\n{key_file}")
                    
                except (ImportError, AttributeError) as e:
                    # If PKCS12 creation fails, try with PyOpenSSL
                    try:
                        import OpenSSL.crypto as crypto
                        
                        # Load the certificate and key from PEM files
                        with open(cert_file, 'rb') as f:
                            cert_data = f.read()
                        
                        with open(key_file, 'rb') as f:
                            key_data = f.read()
                        
                        # Create PKCS12
                        cert_obj = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
                        key_obj = crypto.load_privatekey(crypto.FILETYPE_PEM, key_data)
                        
                        p12 = crypto.PKCS12()
                        p12.set_certificate(cert_obj)
                        p12.set_privatekey(key_obj)
                        pkcs12_data = p12.export(password.encode('utf-8'))
                        
                        # Write PKCS12 file
                        with open(cert_path, "wb") as f:
                            f.write(pkcs12_data)
                        
                        # Show success message
                        self.cert_status.configure(text="Certificate generated", text_color="green")
                        self.show_info("Certificate Generated", 
                                      f"Certificate generated successfully at:\n{cert_path}\n\n"
                                      f"PEM files also available at:\n{cert_file}\n{key_file}")
                        
                    except (ImportError, AttributeError, Exception) as e2:
                        # If both methods fail, just use the PEM files
                        self.cert_status.configure(text="Certificate generated (PEM)", text_color="green")
                        self.show_info("Certificate Generated (PEM format)", 
                                      f"Certificate and key generated in PEM format at:\n{cert_file}\n{key_file}\n\n"
                                      f"Note: PKCS12 format could not be created. Using separate PEM files instead.")
                
            except ImportError:
                # Fall back to PyOpenSSL
                try:
                    import OpenSSL.crypto as crypto
                    
                    # Create a key pair
                    k = crypto.PKey()
                    k.generate_key(crypto.TYPE_RSA, 2048)
                    
                    # Create a self-signed cert
                    cert = crypto.X509()
                    cert.get_subject().C = "US"
                    cert.get_subject().ST = "State"
                    cert.get_subject().L = "City"
                    cert.get_subject().O = "Organization"
                    cert.get_subject().OU = "Organizational Unit"
                    cert.get_subject().CN = common_name
                    cert.set_serial_number(1000)
                    cert.gmtime_adj_notBefore(0)
                    cert.gmtime_adj_notAfter(10*365*24*60*60)  # 10 years
                    cert.set_issuer(cert.get_subject())
                    cert.set_pubkey(k)
                    cert.sign(k, 'sha256')
                    
                    # Export certificate and key to PEM format
                    cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
                    key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, k)
                    
                    # Write PEM files
                    cert_file = cert_path.replace('.p12', '.crt')
                    key_file = cert_path.replace('.p12', '.key')
                    
                    with open(cert_file, 'wb') as f:
                        f.write(cert_pem)
                    
                    with open(key_file, 'wb') as f:
                        f.write(key_pem)
                    
                    # Try to create PKCS12
                    try:
                        p12 = crypto.PKCS12()
                        p12.set_certificate(cert)
                        p12.set_privatekey(k)
                        pkcs12_data = p12.export(password.encode('utf-8'))
                        
                        # Write PKCS12 file
                        with open(cert_path, "wb") as f:
                            f.write(pkcs12_data)
                        
                        # Show success message
                        self.cert_status.configure(text="Certificate generated", text_color="green")
                        self.show_info("Certificate Generated", 
                                      f"Certificate generated successfully at:\n{cert_path}\n\n"
                                      f"PEM files also available at:\n{cert_file}\n{key_file}")
                    
                    except (AttributeError, Exception) as e:
                        # If PKCS12 creation fails, just use the PEM files
                        self.cert_status.configure(text="Certificate generated (PEM)", text_color="green")
                        self.show_info("Certificate Generated (PEM format)", 
                                      f"Certificate and key generated in PEM format at:\n{cert_file}\n{key_file}\n\n"
                                      f"Note: PKCS12 format could not be created. Using separate PEM files instead.")
                    
                except ImportError:
                    self.show_error("Missing Dependencies", 
                                   "Neither cryptography nor PyOpenSSL is available.\n"
                                   "Please install one of these packages:\n"
                                   "pip install cryptography\n"
                                   "pip install pyopenssl")
        
        except Exception as e:
            self.show_error("Certificate Generation Failed", f"Error: {str(e)}")
    
    def view_certificate(self):
        """View certificate details"""
        try:
            cert_path = self.cert_path_entry.get()
            
            # Check if the certificate file exists
            if not os.path.exists(cert_path):
                # If the file doesn't exist, check if it's in a different format
                base_path = os.path.splitext(cert_path)[0]
                possible_extensions = ['.p12', '.crt', '.pem', '.cer']
                found = False
                
                for ext in possible_extensions:
                    alt_path = base_path + ext
                    if os.path.exists(alt_path):
                        cert_path = alt_path
                        found = True
                        break
                
                if not found:
                    self.show_error("Certificate Not Found", f"No certificate found at:\n{cert_path}")
                    return
            
            # Try different methods to view the certificate
            try:
                # First try with cryptography library
                from cryptography import x509
                from cryptography.hazmat.backends import default_backend
                
                # Read the certificate file
                with open(cert_path, 'rb') as f:
                    cert_data = f.read()
                
                # Try to parse as PEM
                try:
                    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                    
                    # Extract certificate details
                    subject = cert.subject
                    issuer = cert.issuer
                    
                    # Format subject and issuer
                    subject_str = "Unknown"
                    issuer_str = "Unknown"
                    
                    for attr in subject:
                        if attr.oid._name == 'commonName':
                            subject_str = attr.value
                    
                    for attr in issuer:
                        if attr.oid._name == 'commonName':
                            issuer_str = attr.value
                    
                    # Get validity dates
                    not_before = cert.not_valid_before.strftime('%Y-%m-%d %H:%M:%S')
                    not_after = cert.not_valid_after.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Create info message
                    info = f"Certificate Details:\n\n"
                    info += f"Certificate File: {os.path.basename(cert_path)}\n"
                    info += f"Subject: {subject_str}\n"
                    info += f"Issuer: {issuer_str}\n"
                    info += f"Valid From: {not_before}\n"
                    info += f"Valid To: {not_after}\n"
                    info += f"Path: {cert_path}"
                    
                    self.show_info("Certificate Information", info)
                    return
                    
                except Exception:
                    # If PEM parsing fails and it's a .p12 file, try to parse as PKCS12
                    if cert_path.endswith('.p12'):
                        # We can't easily parse PKCS12 with cryptography without the password
                        # So we'll fall back to PyOpenSSL or just show basic info
                        pass
            
            except ImportError:
                # Fall back to PyOpenSSL
                try:
                    import OpenSSL.crypto as crypto
                    
                    # Read the certificate file
                    with open(cert_path, 'rb') as f:
                        cert_data = f.read()
                    
                    # Try to parse as PEM
                    try:
                        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
                        
                        # Extract certificate details
                        subject = cert.get_subject()
                        issuer = cert.get_issuer()
                        
                        # Format subject and issuer
                        subject_str = f"CN={subject.CN}" if hasattr(subject, 'CN') else "Unknown"
                        issuer_str = f"CN={issuer.CN}" if hasattr(issuer, 'CN') else "Unknown"
                        
                        # Get validity dates
                        from datetime import datetime
                        not_before = datetime.strptime(cert.get_notBefore().decode('ascii'), '%Y%m%d%H%M%SZ').strftime('%Y-%m-%d %H:%M:%S')
                        not_after = datetime.strptime(cert.get_notAfter().decode('ascii'), '%Y%m%d%H%M%SZ').strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Create info message
                        info = f"Certificate Details:\n\n"
                        info += f"Subject: {subject_str}\n"
                        info += f"Issuer: {issuer_str}\n"
                        info += f"Valid From: {not_before}\n"
                        info += f"Valid To: {not_after}\n"
                        info += f"Path: {cert_path}"
                        
                        self.show_info("Certificate Information", info)
                        return
                        
                    except Exception:
                        # If PEM parsing fails and it's a .p12 file, we can't easily view it
                        if cert_path.endswith('.p12'):
                            # We need the password to view PKCS12
                            pass
                
                except ImportError:
                    # If neither cryptography nor PyOpenSSL is available, show basic info
                    pass
            
            # If we get here, we couldn't parse the certificate with the available libraries
            # Just show basic file info
            import os
            file_size = os.path.getsize(cert_path)
            file_time = os.path.getmtime(cert_path)
            from datetime import datetime
            mod_time = datetime.fromtimestamp(file_time).strftime('%Y-%m-%d %H:%M:%S')
            
            info = f"Certificate File Information:\n\n"
            info += f"Path: {cert_path}\n"
            info += f"Size: {file_size} bytes\n"
            info += f"Last Modified: {mod_time}\n\n"
            info += "Note: Detailed certificate information could not be extracted.\n"
            info += "This may be due to the file format or missing libraries."
            
            self.show_info("Certificate Information", info)
            
        except Exception as e:
            self.show_error("Certificate Error", f"Error: {str(e)}")
    
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
        self.version_override_var = ctk.BooleanVar(value=False)
        override_checkbox = ctk.CTkCheckBox(
            grid_frame, 
            text="Enable Version Override", 
            variable=self.version_override_var,
            command=self.toggle_version_override
        )
        override_checkbox.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.create_tooltip(override_checkbox, "Enable to specify custom versions for each component type")
        
        # POS Version
        pos_label = ctk.CTkLabel(grid_frame, text="POS Version:")
        pos_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.pos_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.pos_version_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.config_manager.register_entry("pos_version", self.pos_version_entry)
        self.create_tooltip(pos_label, "Version for POS components (applies to all POS system types)")
        self.create_tooltip(self.pos_version_entry, "Example: v1.0.0")
        
        # WDM Version
        wdm_label = ctk.CTkLabel(grid_frame, text="WDM Version:")
        wdm_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.wdm_version_entry = ctk.CTkEntry(grid_frame, width=200)
        self.wdm_version_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.config_manager.register_entry("wdm_version", self.wdm_version_entry)
        self.create_tooltip(wdm_label, "Version for WDM components (applies to all WDM system types)")
        self.create_tooltip(self.wdm_version_entry, "Example: v1.0.0")
        
        # Register the override checkbox with config manager
        self.config_manager.register_entry("use_version_override", self.version_override_var)
        
        # Initialize state based on config
        self.toggle_version_override()
    
    def toggle_version_override(self):
        """Toggle the enabled state of version fields based on checkbox"""
        enabled = self.version_override_var.get()
        state = "normal" if enabled else "disabled"
        
        # Update entry states
        self.pos_version_entry.configure(state=state)
        self.wdm_version_entry.configure(state=state)
    
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
        self.create_tooltip(label, "Directory where generated installation files will be saved")
        
        # Entry with tooltip
        self.output_dir_entry = ctk.CTkEntry(frame, width=400)
        self.output_dir_entry.pack(side="left", padx=10)
        self.output_dir_entry.insert(0, self.config_manager.config["output_dir"])
        
        # Create tooltip for the entry
        self.create_tooltip(self.output_dir_entry, "Directory where generated installation files will be saved")
        
        # Browse button with tooltip
        browse_btn = ctk.CTkButton(
            frame,
            text="Browse",
            width=100,
            command=self.browse_output_dir
        )
        browse_btn.pack(side="left", padx=10)
        
        # Create tooltip for the browse button
        self.create_tooltip(browse_btn, "Select output directory")
        
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
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(fill="x", padx=10, pady=20)
        
        # Generate Project button with tooltip
        generate_btn = ctk.CTkButton(
            button_frame,
            text="Generate Project",
            width=200,
            command=lambda: self.project_generator.generate(self.config_manager.config)
        )
        generate_btn.pack(side="left", padx=10)
        self.create_tooltip(generate_btn, "Generate installation scripts based on current configuration")
        
        # Offline Package Creator button with tooltip
        offline_btn = ctk.CTkButton(
            button_frame,
            text="Offline Package Creator",
            width=200,
            command=self.open_offline_package_creator
        )
        offline_btn.pack(side="left", padx=10)
        self.create_tooltip(offline_btn, "Open the Offline Package Creator to download and create offline installation packages")
    
    def browse_output_dir(self):
        directory = ctk.filedialog.askdirectory(initialdir=".")
        if directory:
            self.output_dir_entry.delete(0, "end")
            self.output_dir_entry.insert(0, directory)
    
    def on_window_close(self):
        """Handle window close event"""
        # Ensure all configuration is saved before exit
        try:
            # Update config from all entries
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
            project_generator=self.project_generator
        )
    
    def create_webdav_browser(self):
        # Create WebDAV browser frame
        webdav_frame = ctk.CTkFrame(self.main_frame)
        webdav_frame.pack(fill="x", padx=10, pady=(0, 20))
        
        # Title
        title_label = ctk.CTkLabel(
            webdav_frame,
            text="WebDAV Browser",
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(anchor="w", padx=10, pady=10)
        
        # Description
        description = ctk.CTkLabel(
            webdav_frame,
            text="Browse and download files from the WebDAV server.\n"
                 "Connect to the server using your credentials and navigate to the desired files.",
            justify="left"
        )
        description.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Current path
        self.path_label = ctk.CTkLabel(webdav_frame, text="Current Path: /")
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
        
        # Register WebDAV username with config manager
        self.config_manager.register_entry("webdav_username", self.webdav_username)
        
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
        
        # Register WebDAV password with config manager
        self.config_manager.register_entry("webdav_password", self.webdav_password)
            
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
        
        # Directory listing
        self.dir_listbox = ctk.CTkScrollableFrame(webdav_frame, height=200)
        self.dir_listbox.pack(fill="x", padx=10, pady=5)
    
    def connect_webdav(self):
        """Handle WebDAV connection"""
        base_url = self.config_manager.config["base_url"]
        username = self.webdav_username.get()
        password = self.webdav_password.get()
        
        if not all([base_url, username, password]):
            self.webdav_status.configure(
                text="Error: Base URL, username, and password are required",
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
        """Create offline installation package"""
        try:
            print("\nStarting offline package creation...")
            config = self.config_manager.config
            
            # Get selected components
            selected_components = []
            if self.pos_var.get():
                selected_components.append("POS")
            if self.wdm_var.get():
                selected_components.append("WDM")
            
            if not selected_components:
                self.show_error("Error", "Please select at least one component")
                return
            
            # Call prepare_offline_package with selected components
            success, message = self.project_generator.prepare_offline_package(
                config,
                selected_components
            )
            
            if success:
                self.show_info("Success", message)
            else:
                self.show_error("Error", message)
                
        except Exception as e:
            print(f"Error: {str(e)}")
            self.show_error("Error", f"Failed to create offline package: {str(e)}")
    
    def show_error(self, title, message):
        """Show error dialog"""
        messagebox.showerror(title, message)

    def show_info(self, title, message):
        """Show info dialog"""
        messagebox.showinfo(title, message)

    def get_basic_auth_password_from_keepass(self):
        """Open a dialog to get Basic Auth Password from KeePass"""
        # Create a toplevel window
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("KeePass Authentication")
        dialog.geometry("450x400")  # Increased height to accommodate new elements
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Username frame
        username_frame = ctk.CTkFrame(dialog)
        username_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkLabel(username_frame, text="Username:", width=100).pack(side="left")
        username_var = ctk.StringVar()
        username_entry = ctk.CTkEntry(username_frame, width=200, textvariable=username_var)
        username_entry.pack(side="left", padx=5)
        
        # Password frame
        password_frame = ctk.CTkFrame(dialog)
        password_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkLabel(password_frame, text="Password:", width=100).pack(side="left")
        password_var = ctk.StringVar()
        password_entry = ctk.CTkEntry(password_frame, width=200, textvariable=password_var, show="*")
        password_entry.pack(side="left", padx=5)
        
        # Connect button frame
        connect_frame = ctk.CTkFrame(dialog)
        connect_frame.pack(pady=10, fill="x", padx=20)
        
        connect_btn = ctk.CTkButton(
            connect_frame,
            text="Connect to KeePass",
            width=200,
            command=lambda: connect()
        )
        connect_btn.pack(pady=5)
        
        # Project frame
        project_frame = ctk.CTkFrame(dialog)
        project_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkLabel(project_frame, text="Project:", width=100).pack(side="left")
        project_var = ctk.StringVar(value="AZR-CSE")  # Default project
        project_entry = ctk.CTkEntry(project_frame, width=200, textvariable=project_var)
        project_entry.pack(side="left", padx=5)
        
        # Detect Projects button (initially disabled)
        detect_projects_btn = ctk.CTkButton(
            project_frame,
            text="Detect Projects",
            width=120,
            command=lambda: detect_projects(),
            state="disabled"
        )
        detect_projects_btn.pack(side="left", padx=5)
        
        # Environment frame (will be populated after connection)
        env_frame = ctk.CTkFrame(dialog)
        env_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkLabel(env_frame, text="Environment:", width=100).pack(side="left")
        env_var = ctk.StringVar()
        env_combo = ctk.CTkComboBox(env_frame, width=200, variable=env_var, state="readonly")
        env_combo.pack(side="left", padx=5)
        
        # Status label
        status_var = ctk.StringVar()
        status_label = ctk.CTkLabel(dialog, textvariable=status_var)
        status_label.pack(pady=5)
        
        # Get Password button (initially disabled)
        get_password_btn = ctk.CTkButton(
            dialog,
            text="Get Password",
            command=lambda: get_password(),
            state="disabled"
        )
        get_password_btn.pack(pady=5)
        
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
                project_dialog.geometry("300x450")  # Increased height for filter controls
                project_dialog.transient(dialog)
                project_dialog.grab_set()
                
                # Add label
                ctk.CTkLabel(
                    project_dialog,
                    text="Available Projects:",
                    font=("Helvetica", 14, "bold")
                ).pack(padx=20, pady=(10, 5))
                
                # Add filter controls
                filter_frame = ctk.CTkFrame(project_dialog)
                filter_frame.pack(padx=20, pady=(0, 10), fill="x")
                
                # Filter checkbox
                show_azr_only_var = ctk.BooleanVar(value=True)  # Default to showing only AZR projects
                
                def update_project_list():
                    # Clear existing buttons
                    for widget in projects_frame.winfo_children():
                        widget.destroy()
                    
                    # Filter projects based on checkbox state
                    filtered_projects = projects
                    if show_azr_only_var.get():
                        filtered_projects = [p for p in projects if p['name'].startswith('AZR-')]
                    
                    # Sort projects alphabetically
                    filtered_projects.sort(key=lambda x: x['name'].lower())
                    
                    # Show count
                    count_label.configure(text=f"Showing {len(filtered_projects)} of {len(projects)} projects")
                    
                    # Add buttons for each project
                    for project in filtered_projects:
                        btn = ctk.CTkButton(
                            projects_frame,
                            text=project['name'],
                            width=200,
                            command=lambda p=project: select_project(p)
                        )
                        btn.pack(pady=2)
                
                azr_checkbox = ctk.CTkCheckBox(
                    filter_frame,
                    text="Show only AZR projects",
                    variable=show_azr_only_var,
                    command=update_project_list
                )
                azr_checkbox.pack(side="left", padx=5)
                
                # Count label
                count_label = ctk.CTkLabel(filter_frame, text="")
                count_label.pack(side="right", padx=5)
                
                # Create scrollable frame for projects
                projects_frame = ctk.CTkScrollableFrame(project_dialog, width=250, height=300)
                projects_frame.pack(padx=20, pady=10, fill="both", expand=True)
                
                # Add search field
                search_frame = ctk.CTkFrame(project_dialog)
                search_frame.pack(padx=20, pady=(0, 10), fill="x")
                
                ctk.CTkLabel(search_frame, text="Search:", width=50).pack(side="left", padx=5)
                search_var = ctk.StringVar()
                
                def on_search_change(*args):
                    search_text = search_var.get().lower()
                    
                    # Clear existing buttons
                    for widget in projects_frame.winfo_children():
                        widget.destroy()
                    
                    # Filter projects based on checkbox state and search text
                    filtered_projects = projects
                    if show_azr_only_var.get():
                        filtered_projects = [p for p in projects if p['name'].startswith('AZR-')]
                    
                    if search_text:
                        filtered_projects = [p for p in filtered_projects if search_text in p['name'].lower()]
                    
                    # Sort projects alphabetically
                    filtered_projects.sort(key=lambda x: x['name'].lower())
                    
                    # Update count
                    count_label.configure(text=f"Showing {len(filtered_projects)} of {len(projects)} projects")
                    
                    # Add buttons for each project
                    for project in filtered_projects:
                        btn = ctk.CTkButton(
                            projects_frame,
                            text=project['name'],
                            width=200,
                            command=lambda p=project: select_project(p)
                        )
                        btn.pack(pady=2)
                
                search_var.trace_add("write", on_search_change)
                search_entry = ctk.CTkEntry(search_frame, width=180, textvariable=search_var)
                search_entry.pack(side="left", padx=5)
                
                def select_project(project):
                    # Set the selected project
                    project_var.set(project['name'])
                    project_dialog.destroy()
                    
                    # Now get environments for this project
                    folder_id = project['id']
                    folder_contents = client.get_folder(folder_id)
                    subfolders = self.get_subfolders(folder_contents)
                    
                    # Update environment dropdown
                    env_values = [folder['name'] for folder in subfolders]
                    env_combo.configure(values=env_values)
                    if env_values:
                        env_combo.set(env_values[0])
                    
                    # Store folder contents for later use
                    dialog.folder_contents = folder_contents
                    
                    status_var.set(f"Selected project: {project['name']}")
                
                # Initialize the project list
                update_project_list()
            
            except Exception as e:
                status_var.set(f"Error detecting projects: {str(e)}")
        
        # Connect to KeePass and get environments
        def connect():
            try:
                status_var.set("Connecting to KeePass...")
                
                client = PleasantPasswordClient(
                    base_url="https://keeserver.gk.gk-software.com/api/v5/rest/",
                    username=username_var.get(),
                    password=password_var.get()
                )
                
                # Store client for later use
                dialog.client = client
                
                # Get project folder
                projects_folder_id = "87300a24-9741-4d24-8a5c-a8b04e0b7049"
                folder_structure = client.get_folder(projects_folder_id)
                
                # Find project folder
                project_name = project_var.get()
                folder_id = self.find_folder_id_by_name(folder_structure, project_name)
                
                if folder_id:
                    # Get environments
                    folder_contents = client.get_folder(folder_id)
                    subfolders = self.get_subfolders(folder_contents)
                    
                    # Update environment dropdown
                    env_values = [folder['name'] for folder in subfolders]
                    env_combo.configure(values=env_values)
                    if env_values:
                        env_combo.set(env_values[0])
                    
                    status_var.set("Connected successfully! Select environment and get password.")
                    get_password_btn.configure(state="normal")
                    detect_projects_btn.configure(state="normal")  # Enable Detect Projects button
                    
                    # Store folder contents for later use
                    dialog.folder_contents = folder_contents
                else:
                    status_var.set(f"Project {project_name} not found! Click 'Detect Projects' to see available projects.")
                    detect_projects_btn.configure(state="normal")  # Enable Detect Projects button
            
            except Exception as e:
                status_var.set(f"Error: {str(e)}")
        
        # Get password after selecting environment
        def get_password():
            try:
                client = dialog.client
                folder_contents = dialog.folder_contents
                
                # Find selected environment folder
                env_name = env_var.get()
                env_folder = None
                
                for subfolder in self.get_subfolders(folder_contents):
                    if subfolder['name'] == env_name:
                        env_folder = subfolder
                        break
                
                if env_folder:
                    # Get full folder structure with higher recurse level
                    print("\nGetting folder structure for environment:", env_name)
                    print(f"Folder ID: {env_folder['id']}")
                    folder_structure = client.get_folder_by_id(env_folder['id'], recurse_level=5)
                    
                    # Print the raw JSON response for debugging
                    import json
                    print("\n=== RAW JSON RESPONSE FROM KEEPASS API ===")
                    print(json.dumps(folder_structure, indent=2)[:2000])  # Print first 2000 chars to avoid flooding console
                    print("... (truncated)")
                    print("=== END OF RAW JSON RESPONSE ===\n")
                    
                    # Print all credentials in the folder structure for debugging
                    print("\nAll credentials in the folder structure:")
                    self.print_all_credentials(folder_structure)
                    
                    # Find password entry - look for TEST-LAUNCHPAD-OAUTH-BA-PASSWORD first
                    basic_auth_entry = self.find_basic_auth_password_entry(folder_structure)
                    if basic_auth_entry:
                        # Debug output
                        print(f"\nFound BASIC-AUTH entry: {basic_auth_entry['Id']}")
                        print(f"Entry name: {basic_auth_entry['Name']}")
                        print("Attempting to get password...")
                        
                        # Get password - direct API call
                        try:
                            password_url = f"credentials/{basic_auth_entry['Id']}/password"
                            print(f"Making API call to: {password_url}")
                            password = client._make_request('GET', password_url)
                            print(f"Password response type: {type(password)}")
                            print(f"Password response: {password}")
                            
                            # Set password directly as string
                            actual_password = str(password).strip()
                            print(f"Setting password: {actual_password}")
                            
                            # Set password in Basic Auth Password field
                            self.basic_auth_password_entry.delete(0, 'end')
                            self.basic_auth_password_entry.insert(0, actual_password)
                            print("Password set in field successfully")
                            
                            status_var.set("Password retrieved successfully!")
                            dialog.after(1000, dialog.destroy)  # Close after 1 second
                        except Exception as e:
                            print(f"Error getting password: {str(e)}")
                            status_var.set(f"Error getting password: {str(e)}")
                    else:
                        status_var.set(f"No Basic Auth password entry found in {env_name}!")
                else:
                    status_var.set(f"Environment {env_name} not found!")
            
            except Exception as e:
                status_var.set(f"Error: {str(e)}")
    
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
        # This is a simple tooltip implementation
        # When mouse enters the widget, show tooltip
        def enter(event):
            # Create a toplevel window for the tooltip
            tooltip = ctk.CTkToplevel(self.window)
            tooltip.wm_overrideredirect(True)  # Remove window decorations
            tooltip.wm_geometry(f"+{event.x_root+15}+{event.y_root+10}")
            
            # Create a label with the tooltip text
            label = ctk.CTkLabel(
                tooltip,
                text=text,
                corner_radius=6,
                fg_color=("#333333", "#666666"),  # Dark background
                text_color=("#FFFFFF", "#FFFFFF"),  # White text
                padx=10,
                pady=5
            )
            label.pack()
            
            # Store the tooltip reference in the widget
            widget.tooltip = tooltip
            
        # When mouse leaves the widget, hide tooltip
        def leave(event):
            if hasattr(widget, "tooltip"):
                widget.tooltip.destroy()
                delattr(widget, "tooltip")
        
        # Bind events
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def run(self):
        self.window.mainloop()

# New class for the Offline Package Creator window
class OfflinePackageCreator:
    def __init__(self, parent, config_manager, project_generator):
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Offline Package Creator")
        self.window.geometry("1000x800")
        self.window.transient(parent)  # Set to be on top of the parent window
        
        # Store references
        self.config_manager = config_manager
        self.project_generator = project_generator
        
        # Create main container with scrollbar
        self.main_frame = ctk.CTkScrollableFrame(self.window, width=900, height=700)
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Create WebDAV browser
        self.create_webdav_browser()
        
        # Create offline package section
        self.create_offline_package_section()
    
    def create_offline_package_section(self):
        """Create the offline package creation section"""
        # Create frame
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", padx=10, pady=(20, 10))
        
        # Title
        title_label = ctk.CTkLabel(
            frame,
            text="Create Offline Package",
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(anchor="w", padx=10, pady=10)
        
        # Description
        description = ctk.CTkLabel(
            frame,
            text="Create an offline installation package that can be used without internet connection.\n"
                 "Select the components you want to include in the package.",
            justify="left"
        )
        description.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Component selection frame
        component_frame = ctk.CTkFrame(frame)
        component_frame.pack(fill="x", padx=10, pady=10)
        
        # Add checkboxes for components
        self.pos_var = ctk.BooleanVar(value=True)
        self.wdm_var = ctk.BooleanVar(value=True)
        
        pos_checkbox = ctk.CTkCheckBox(
            component_frame,
            text="POS Component",
            variable=self.pos_var
        )
        pos_checkbox.pack(side="left", padx=20, pady=10)
        
        wdm_checkbox = ctk.CTkCheckBox(
            component_frame,
            text="WDM Component",
            variable=self.wdm_var
        )
        wdm_checkbox.pack(side="left", padx=20, pady=10)
        
        # Create button
        create_btn = ctk.CTkButton(
            frame,
            text="Create Offline Package",
            width=200,
            command=self.create_offline_package
        )
        create_btn.pack(anchor="center", padx=10, pady=20)
    
    def create_webdav_browser(self):
        # Create WebDAV browser frame
        webdav_frame = ctk.CTkFrame(self.main_frame)
        webdav_frame.pack(fill="x", padx=10, pady=(0, 20))
        
        # Title
        title_label = ctk.CTkLabel(
            webdav_frame,
            text="WebDAV Browser",
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(anchor="w", padx=10, pady=10)
        
        # Description
        description = ctk.CTkLabel(
            webdav_frame,
            text="Browse and download files from the WebDAV server.\n"
                 "Connect to the server using your credentials and navigate to the desired files.",
            justify="left"
        )
        description.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Current path
        self.path_label = ctk.CTkLabel(webdav_frame, text="Current Path: /")
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
        
        # Register WebDAV username with config manager
        self.config_manager.register_entry("webdav_username", self.webdav_username)
        
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
        
        # Register WebDAV password with config manager
        self.config_manager.register_entry("webdav_password", self.webdav_password)
            
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
        
        # Directory listing
        self.dir_listbox = ctk.CTkScrollableFrame(webdav_frame, height=200)
        self.dir_listbox.pack(fill="x", padx=10, pady=5)
    
    def connect_webdav(self):
        """Handle WebDAV connection"""
        base_url = self.config_manager.config["base_url"]
        username = self.webdav_username.get()
        password = self.webdav_password.get()
        
        if not all([base_url, username, password]):
            self.webdav_status.configure(
                text="Error: Base URL, username, and password are required",
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
        """Create offline installation package"""
        try:
            print("\nStarting offline package creation...")
            config = self.config_manager.config
            
            # Get selected components
            selected_components = []
            if self.pos_var.get():
                selected_components.append("POS")
            if self.wdm_var.get():
                selected_components.append("WDM")
            
            if not selected_components:
                self.show_error("Error", "Please select at least one component")
                return
            
            # Call prepare_offline_package with selected components
            success, message = self.project_generator.prepare_offline_package(
                config,
                selected_components
            )
            
            if success:
                self.show_info("Success", message)
            else:
                self.show_error("Error", message)
                
        except Exception as e:
            print(f"Error: {str(e)}")
            self.show_error("Error", f"Failed to create offline package: {str(e)}")
    
    def show_error(self, title, message):
        """Show error dialog"""
        messagebox.showerror(title, message)

    def show_info(self, title, message):
        """Show info dialog"""
        messagebox.showinfo(title, message)

def main():
    app = GKInstallBuilder()
    app.run()

if __name__ == "__main__":
    main() 