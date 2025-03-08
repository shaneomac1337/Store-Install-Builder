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
        self.config_file = "gk_install_config.json"
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

    def get_entry(self, key):
        """Get an entry widget by its key"""
        return self.entries.get(key, None)

    def update_entry_value(self, key, value):
        """Update an entry widget with a new value, clearing any existing content first"""
        entry = self.get_entry(key)
        if entry and hasattr(entry, "delete") and hasattr(entry, "insert"):
            entry.delete(0, 'end')  # Clear existing value
            entry.insert(0, value)  # Insert new value
            self.config[key] = value  # Update config dictionary
            return True
        return False

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
        # Use the safer method instead
        return self.safe_update_config_from_entries()

    def load_config(self):
        """Load configuration from file or return default values"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)
                print(f"Configuration loaded from {self.config_file}")
            except Exception as e:
                print(f"Error loading configuration: {e}")
                self.config = self._get_default_config()
        else:
            print(f"Configuration file {self.config_file} not found, using defaults")
            self.config = self._get_default_config()

    def _get_default_config(self):
        """Return default configuration with descriptive examples"""
        return {
            # Project Configuration
            "project_name": "My Store Project",
            "base_url": "example.cloud4retail.co",
            "version": "v1.0.0",
            
            # Platform Selection
            "platform": "Windows",  # Default platform (Windows or Linux)
            
            # Component-specific versions
            "use_version_override": False,  # Flag to enable/disable version override
            "pos_version": "v1.0.0",
            "wdm_version": "v1.0.0",
            "flow_service_version": "v1.0.0",
            "lpa_service_version": "v1.0.0",
            "storehub_service_version": "v1.0.0",
            
            # Installation Configuration
            "base_install_dir": "C:\\gkretail",  # Will be adjusted based on platform
            "tenant_id": "001",
            "pos_system_type": "",  # Will be dynamically set based on URL
            "wdm_system_type": "",  # Will be dynamically set based on URL
            "flow_service_system_type": "GKR-FLOWSERVICE-CLOUD",  # Default to GKR but still configurable
            "lpa_service_system_type": "",  # Will be dynamically set based on URL
            "storehub_service_system_type": "",  # Will be dynamically set based on URL
            "firebird_server_path": "localhost",
            
            # Security Configuration
            "ssl_password": "changeit",
            "eh_launchpad_username": "1001",
            "eh_launchpad_password": "gkgkgk123!",
            "auth_service_ba_user": "launchpad",
            "launchpad_oauth2": "Enter Auth-service's pre-defined Launchpad password",
            "form_username": "1001",
            "form_password": "Enter your Launchpad password",
            
            # Certificate Configuration
            "certificate_path": "PROJECT/BASEURL/certificate.p12",  # Will be dynamically set based on URL
            "certificate_common_name": "*gk-software.com",
            
            # Output Configuration
            "output_dir": "PROJECT/BASEURL",  # Will be dynamically set based on URL
            
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
            
            # Update config from entries using the safer method
            self.safe_update_config_from_entries()
            
            # Save to file
            with open(self.config_file, "w") as f:
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
            # Update config from entries using the safer method
            self.safe_update_config_from_entries()
            
            # Save to file
            with open(self.config_file, "w") as f:
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

    def unregister_entry(self, key):
        """Unregister an entry widget for a config key"""
        if key in self.entries:
            # Save the current value to config before unregistering
            try:
                entry = self.entries[key]
                if hasattr(entry, 'get'):
                    try:
                        # Only try to get the value if the widget exists
                        if hasattr(entry, 'winfo_exists') and entry.winfo_exists():
                            self.config[key] = entry.get()
                    except Exception:
                        # If we can't get the value, keep the existing config value
                        pass
            except Exception:
                # Ignore any errors when trying to save the value
                pass
                
            # Remove the entry from our dictionary
            del self.entries[key]
            
    def safe_update_config_from_entries(self):
        """Update config from registered entries, skipping any that cause errors"""
        for key, entry in list(self.entries.items()):
            try:
                if hasattr(entry, "get"):
                    # Only try to get the value if the widget exists
                    if not hasattr(entry, 'winfo_exists') or entry.winfo_exists():
                        self.config[key] = entry.get()
                    else:
                        # Widget doesn't exist, unregister it
                        self.unregister_entry(key)
            except Exception:
                # If there's any error, unregister the entry
                try:
                    self.unregister_entry(key)
                except Exception:
                    pass
        return self.config 