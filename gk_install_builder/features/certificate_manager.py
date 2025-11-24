import os
import customtkinter as ctk
import subprocess
import tempfile
from tkinter import messagebox

try:
    from gk_install_builder.utils.tooltips import create_tooltip
except ImportError:
    from utils.tooltips import create_tooltip

class CertificateManager:
    """Manages SSL certificate generation and configuration"""

    def __init__(self, parent_window, config_manager, main_app):
        self.root = parent_window
        self.config_manager = config_manager
        self.main_app = main_app

        # Certificate entry references
        self.cert_path_entry = None
        self.cert_common_name_entry = None
        self.cert_status_label = None

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        return create_tooltip(widget, text, parent_window=self.root)

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

            # Get SSL password from main app if available
            password = "changeit"
            if hasattr(self.main_app, 'ssl_password_entry') and self.main_app.ssl_password_entry:
                password = self.main_app.ssl_password_entry.get() or "changeit"

            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(cert_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"Created directory: {output_dir}")

            # Generate certificate using OpenSSL directly
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

                # Create clean environment without PyInstaller's library paths
                clean_env = os.environ.copy()
                # Remove LD_LIBRARY_PATH that PyInstaller sets, which causes library conflicts
                clean_env.pop('LD_LIBRARY_PATH', None)

                # Generate key
                subprocess.run(
                    ['openssl', 'genrsa', '-out', temp_key_path, '2048'],
                    check=True, capture_output=True, env=clean_env
                )

                # Generate certificate
                subprocess.run(
                    ['openssl', 'req', '-new', '-x509', '-key', temp_key_path,
                     '-out', temp_cert_path, '-days', '3650', '-config', config_file],
                    check=True, capture_output=True, env=clean_env
                )

                # Convert to PKCS12
                subprocess.run(
                    ['openssl', 'pkcs12', '-export', '-out', cert_path,
                     '-inkey', temp_key_path, '-in', temp_cert_path,
                     '-password', f'pass:{password}'],
                    check=True, capture_output=True, env=clean_env
                )

                # Clean up the temporary files
                os.unlink(config_file)
                os.unlink(temp_cert_path)
                os.unlink(temp_key_path)

                # Show success message
                self.cert_status_label.configure(text="Certificate generated", text_color="green")
                messagebox.showinfo(
                    "Certificate Generated",
                    f"Certificate generated successfully at:\n{cert_path}\n\n"
                    f"Common Name: {common_name}\n"
                    f"Subject Alternative Name (SAN): {common_name}\n"
                    f"Valid for: 10 years"
                )

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
                messagebox.showerror("Certificate Generation Failed", f"Error: {str(e2)}")
                return False

        except Exception as e:
            self.cert_status_label.configure(text="Certificate generation failed", text_color="red")
            messagebox.showerror("Certificate Generation Failed", f"Error: {str(e)}")
            return False
