import json
import os
import customtkinter as ctk

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()
        self.entries = {}

    def register_entry(self, key, entry):
        """Register a GUI entry widget for a config key"""
        self.entries[key] = entry

    def load_config(self):
        """Load configuration from JSON file"""
        try:
            if os.path.exists('gk_install_config.json'):
                with open('gk_install_config.json', 'r') as f:
                    return json.load(f)
            else:
                return {
                    "project_name": "CSE Test",
                    "base_url": "test.cse.cloud4retail.co",
                    "version": "v1.0.0",
                    "base_install_dir": "C:\\gkretail",
                    "ssl_password": "changeit",
                    "username": "launchpad",
                    "form_username": "1001",
                    "output_dir": "generated_scripts",
                    "tenant_id": "001",
                    "basic_auth_password": "",
                    "form_password": "",
                    "pos_system_type": "GKR-OPOS-CLOUD",
                    "wdm_system_type": "CSE-wdm"
                }
        except Exception as e:
            self._show_error("Failed to load configuration", str(e))

    def save_config(self):
        """Save current configuration to JSON file"""
        try:
            # Update config from GUI entries
            for key, entry in self.entries.items():
                self.config[key] = entry.get()
            
            # Save to file
            with open('gk_install_config.json', 'w') as f:
                json.dump(self.config, f, indent=4)
            
            self._show_info("Success", "Configuration saved successfully!")
        except Exception as e:
            self._show_error("Failed to save configuration", str(e))

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