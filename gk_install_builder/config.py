import json
import os
import customtkinter as ctk
import threading
import time

class ConfigManager:
    def __init__(self):
        self.config = {}
        self.entries = {}
        self.save_status_label = None
        self.save_timer = None
        self.save_in_progress = False
        self.load_config()

    def register_entry(self, key, entry):
        """Register an entry widget for a config key"""
        self.entries[key] = entry
        
        # Add trace to entry for auto-save
        if hasattr(entry, "bind"):
            entry.bind("<KeyRelease>", lambda event: self.schedule_save())
            
            # For dropdown/combobox, bind to the <<ComboboxSelected>> event
            if str(entry).find("combobox") != -1:
                entry.bind("<<ComboboxSelected>>", lambda event: self.schedule_save())

    def set_save_status_label(self, label):
        """Set the label for displaying save status"""
        self.save_status_label = label

    def _on_entry_change(self, key):
        """Handle entry value change"""
        # Update config with the new value
        entry = self.entries[key]
        if hasattr(entry, 'get'):
            self.config[key] = entry.get()
        
        # Schedule a save after a short delay (debounce)
        self._schedule_save()
        
    def _schedule_save(self):
        """Schedule a save after a short delay to avoid saving too frequently"""
        # Cancel any existing timer
        if self.save_timer:
            self.save_timer.cancel()
        
        # Create a new timer
        self.save_timer = threading.Timer(1.0, self.save_config)
        self.save_timer.daemon = True
        self.save_timer.start()
        
        # Show "Saving..." status
        if self.save_status_label:
            self.save_status_label.configure(text="Saving...", text_color="#FFA500")  # Orange color

    def update_config_from_entries(self):
        """Update config from registered entries"""
        for key, entry in self.entries.items():
            if hasattr(entry, "get"):
                self.config[key] = entry.get()
        return self.config

    def load_config(self):
        """Load configuration from file or return default values"""
        config_file = "gk_install_config.json"
        
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    self.config = json.load(f)
                print(f"Configuration loaded from {config_file}")
            except Exception as e:
                print(f"Error loading configuration: {e}")
                self.config = self._get_default_config()
        else:
            print(f"Configuration file {config_file} not found, using defaults")
            self.config = self._get_default_config()

    def _get_default_config(self):
        """Return default configuration with descriptive examples"""
        return {
            # Project Configuration
            "project_name": "My Store Project",
            "base_url": "example.cloud4retail.co",
            "version": "v1.0.0",
            
            # Component-specific versions
            "use_version_override": False,  # Flag to enable/disable version override
            "pos_version": "v1.0.0",
            "wdm_version": "v1.0.0",
            
            # Installation Configuration
            "base_install_dir": "C:\\gkretail",
            "tenant_id": "001",
            "pos_system_type": "GKR-OPOS-CLOUD",
            "wdm_system_type": "CSE-wdm",
            
            # Security Configuration
            "ssl_password": "changeit",
            "username": "launchpad",
            "form_username": "1001",
            "basic_auth_password": "Enter your basic auth password or use KeePass",
            "form_password": "Enter your form password",
            
            # Output Configuration
            "output_dir": "generated_scripts",
            
            # WebDAV Configuration
            "webdav_username": "Enter your WebDAV username",
            "webdav_password": "Enter your WebDAV password"
        }

    def save_config(self):
        """Save configuration to file"""
        try:
            # Update save status
            if self.save_status_label:
                self.save_status_label.configure(text="Saving...", text_color="orange")
            
            # Set save in progress flag
            self.save_in_progress = True
            
            # Update config from entries
            self.update_config_from_entries()
            
            # Save to file
            with open("gk_install_config.json", "w") as f:
                json.dump(self.config, f, indent=4)
            
            # Update save status
            if self.save_status_label:
                self.save_status_label.configure(text="Saved", text_color="green")
                
                # Clear status after 3 seconds
                if self.save_timer:
                    self.save_timer.cancel()
                self.save_timer = threading.Timer(3, self.clear_save_status)
                self.save_timer.daemon = True
                self.save_timer.start()
            
            # Reset save in progress flag
            self.save_in_progress = False
            
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            
            # Update save status
            if self.save_status_label:
                self.save_status_label.configure(
                    text=f"Save failed: {str(e)}", 
                    text_color="red"
                )
            
            # Reset save in progress flag
            self.save_in_progress = False
            
            return False

    def save_config_silent(self):
        """Save configuration without updating UI"""
        try:
            # Update config from entries
            self.update_config_from_entries()
            
            # Save to file
            with open("gk_install_config.json", "w") as f:
                json.dump(self.config, f, indent=4)
            
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False

    def schedule_save(self):
        """Schedule a save operation after a short delay"""
        # Cancel existing timer if any
        if self.save_timer:
            self.save_timer.cancel()
        
        # Don't schedule if save is already in progress
        if self.save_in_progress:
            return
        
        # Schedule save after 1 second of inactivity
        self.save_timer = threading.Timer(1, self.save_config)
        self.save_timer.daemon = True
        self.save_timer.start()
        
        # Update save status
        if self.save_status_label:
            self.save_status_label.configure(text="Changes pending...", text_color="orange")

    def clear_save_status(self):
        """Clear the save status label"""
        if self.save_status_label:
            self.save_status_label.configure(text="")

    def _show_error(self, title, message):
        """Show error dialog"""
        dialog = ctk.CTkInputDialog(
            text=f"Error: {message}",
            title=title
        )
        dialog.destroy()

    def _show_info(self, title, message):
        """Show info dialog"""
        dialog = ctk.CTkInputDialog(
            text=message,
            title=title
        )
        dialog.destroy() 