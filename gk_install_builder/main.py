import customtkinter as ctk
from config import ConfigManager
from generator import ProjectGenerator
import os
import tkinter.ttk as ttk
import sys

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
        
        self.create_gui()
        
        # Add WebDAV browser frame
        self.create_webdav_browser()  # Always show WebDAV browser
        
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
        
        # Installation Configuration
        self.create_section("Installation Configuration", [
            "Base Install Directory",
            "Tenant ID",
            "POS System Type",
            "WDM System Type"
        ])
        
        # Security Configuration
        self.create_section("Security Configuration", [
            "SSL Password",
            "Username",
            "Form Username",
            "Basic Auth Password",
            "Form Password"
        ])
        
        # Output Directory
        self.create_output_selection()
        
        # Buttons
        self.create_buttons()
        
    def create_section(self, title, fields):
        # Section Frame
        section_frame = ctk.CTkFrame(self.main_frame)
        section_frame.pack(fill="x", padx=10, pady=(0, 20))
        
        # Title
        ctk.CTkLabel(
            section_frame,
            text=title,
            font=("Helvetica", 16, "bold")
        ).pack(anchor="w", padx=10, pady=10)
        
        # Fields
        for field in fields:
            field_frame = ctk.CTkFrame(section_frame)
            field_frame.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(
                field_frame,
                text=f"{field}:",
                width=150
            ).pack(side="left", padx=10)
            
            entry = ctk.CTkEntry(field_frame, width=400)
            entry.pack(side="left", padx=10)
            
            config_key = field.lower().replace(" ", "_")
            if config_key in self.config_manager.config:
                entry.insert(0, self.config_manager.config[config_key])
            
            self.config_manager.register_entry(config_key, entry)
    
    def create_output_selection(self):
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", padx=10, pady=(0, 20))
        
        ctk.CTkLabel(
            frame,
            text="Output Directory:",
            width=150
        ).pack(side="left", padx=10)
        
        self.output_dir_entry = ctk.CTkEntry(frame, width=400)
        self.output_dir_entry.pack(side="left", padx=10)
        self.output_dir_entry.insert(0, self.config_manager.config["output_dir"])
        
        ctk.CTkButton(
            frame,
            text="Browse",
            width=100,
            command=self.browse_output_dir
        ).pack(side="left", padx=10)
        
        self.config_manager.register_entry("output_dir", self.output_dir_entry)
    
    def create_buttons(self):
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(fill="x", padx=10, pady=20)
        
        ctk.CTkButton(
            button_frame,
            text="Save Configuration",
            width=200,
            command=self.config_manager.save_config
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="Generate Project",
            width=200,
            command=lambda: self.project_generator.generate(self.config_manager.config)
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="Create Offline Package",
            width=200,
            command=self.create_offline_package
        ).pack(side="left", padx=10)
    
    def browse_output_dir(self):
        directory = ctk.filedialog.askdirectory(initialdir=".")
        if directory:
            self.output_dir_entry.delete(0, "end")
            self.output_dir_entry.insert(0, directory)
    
    def create_webdav_browser(self):
        # Create WebDAV browser frame
        webdav_frame = ctk.CTkFrame(self.main_frame)
        webdav_frame.pack(fill="x", padx=10, pady=(0, 20))
        
        # Title
        ctk.CTkLabel(
            webdav_frame,
            text="WebDAV Browser",
            font=("Helvetica", 16, "bold")
        ).pack(anchor="w", padx=10, pady=10)
        
        # Current path
        self.path_label = ctk.CTkLabel(webdav_frame, text="Current Path: /")
        self.path_label.pack(anchor="w", padx=10, pady=5)
        
        # Authentication frame
        auth_frame = ctk.CTkFrame(webdav_frame)
        auth_frame.pack(fill="x", padx=10, pady=5)
        
        # Username
        username_frame = ctk.CTkFrame(auth_frame)
        username_frame.pack(side="left", padx=5)
        ctk.CTkLabel(
            username_frame,
            text="Username:",
            width=100
        ).pack(side="left")
        self.webdav_username = ctk.CTkEntry(username_frame, width=150)
        self.webdav_username.pack(side="left", padx=5)
        # Load saved username
        if self.config_manager.config["webdav_username"]:
            self.webdav_username.insert(0, self.config_manager.config["webdav_username"])
        
        # Password
        password_frame = ctk.CTkFrame(auth_frame)
        password_frame.pack(side="left", padx=5)
        ctk.CTkLabel(
            password_frame,
            text="Password:",
            width=100
        ).pack(side="left")
        self.webdav_password = ctk.CTkEntry(password_frame, width=150, show="*")
        self.webdav_password.pack(side="left", padx=5)
        # Load saved password
        if self.config_manager.config["webdav_password"]:
            self.webdav_password.insert(0, self.config_manager.config["webdav_password"])
        
        # Connect button
        ctk.CTkButton(
            auth_frame,
            text="Connect",
            width=100,
            command=self.connect_webdav
        ).pack(side="left", padx=10)
        
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
        
        ctk.CTkButton(
            nav_frame,
            text="Up",
            width=50,
            command=self.navigate_up
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            nav_frame,
            text="Refresh",
            width=70,
            command=self.refresh_listing
        ).pack(side="left", padx=5)
        
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
        
        # Save credentials to config
        self.config_manager.config["webdav_username"] = username
        self.config_manager.config["webdav_password"] = password
        self.config_manager.save_config()
        
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
            
            # Create our own dialog window
            dialog = ctk.CTkToplevel(self.window)
            dialog.title("Select Components")
            dialog.geometry("300x200")
            
            # Add label
            ctk.CTkLabel(
                dialog,
                text="Which components would you like to download?"
            ).pack(padx=20, pady=10)
            
            # Add checkboxes for components
            pos_var = ctk.BooleanVar(value=True)
            wdm_var = ctk.BooleanVar(value=True)
            
            ctk.CTkCheckBox(
                dialog,
                text="POS Component",
                variable=pos_var
            ).pack(padx=20, pady=10)
            
            ctk.CTkCheckBox(
                dialog,
                text="WDM Component",
                variable=wdm_var
            ).pack(padx=20, pady=10)
            
            # Add OK button
            def on_ok():
                dialog.quit()
                dialog.destroy()
                
            ctk.CTkButton(
                dialog,
                text="OK",
                command=on_ok
            ).pack(padx=20, pady=20)
            
            # Wait for dialog
            dialog.grab_set()  # Make dialog modal
            dialog.wait_window()
            
            # Get selected components
            selected_components = []
            if pos_var.get():
                selected_components.append("POS")
            if wdm_var.get():
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
        dialog = ctk.CTkInputDialog(
            text=f"Error: {message}",
            title=title
        )
        dialog.destroy()

    def show_info(self, title, message):
        """Show info dialog"""
        dialog = ctk.CTkInputDialog(
            text=message,
            title=title
        )
        dialog.destroy()
    
    def run(self):
        self.window.mainloop()

def main():
    app = GKInstallBuilder()
    app.run()

if __name__ == "__main__":
    main() 