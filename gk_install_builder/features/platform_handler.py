"""
Platform switching functionality for Store-Install-Builder
Handles switching between Windows and Linux platforms
"""


class PlatformHandler:
    """Manages platform-specific configuration and path conversions"""

    def __init__(self, config_manager):
        """
        Initialize Platform Handler.

        Args:
            config_manager: ConfigManager instance for reading/writing configuration
        """
        self.config_manager = config_manager

    def on_platform_changed(self, platform):
        """
        Handle platform change.

        Args:
            platform: Target platform ("Windows" or "Linux")
        """
        # Update the base install directory based on platform
        if platform == "Windows":
            default_dir = "C:\\gkretail"
            firebird_path = "C:\\Program Files\\Firebird\\Firebird_3_0"
            jaybird_driver_path = "C:\\gkretail\\Jaybird"
            default_detection_dir = "C:\\gkretail\\stations"
        else:  # Linux
            default_dir = "/usr/local/gkretail"
            firebird_path = "/opt/firebird"
            jaybird_driver_path = "/usr/local/gkretail/Jaybird"
            default_detection_dir = "/usr/local/gkretail/stations"

        # Update config values first
        self.config_manager.config["base_install_dir"] = default_dir
        self.config_manager.config["firebird_server_path"] = firebird_path
        self.config_manager.config["firebird_driver_path_local"] = jaybird_driver_path

        # Always update the entry field to match config
        base_dir_entry = self.config_manager.get_entry("base_install_dir")
        if base_dir_entry:
            base_dir_entry.delete(0, 'end')
            base_dir_entry.insert(0, default_dir)

        firebird_entry = self.config_manager.get_entry("firebird_server_path")
        if firebird_entry:
            firebird_entry.delete(0, 'end')
            firebird_entry.insert(0, firebird_path)

        jaybird_entry = self.config_manager.get_entry("firebird_driver_path_local")
        if jaybird_entry:
            jaybird_entry.delete(0, 'end')
            jaybird_entry.insert(0, jaybird_driver_path)

        # Update detection base directory
        # Always update the config values first
        self.config_manager.config["file_detection_base_directory"] = default_detection_dir
        # Also update detection_config to keep in sync
        if "detection_config" in self.config_manager.config:
            self.config_manager.config["detection_config"]["base_directory"] = default_detection_dir

        # If the entry widget exists, update it too
        detection_dir_entry = self.config_manager.get_entry("file_detection_base_directory")
        if detection_dir_entry:
            # Check if widget still exists before trying to access it
            try:
                if detection_dir_entry.winfo_exists():
                    current_detection_dir = detection_dir_entry.get()
                    # Only update if empty or has wrong platform separator
                    if not current_detection_dir or \
                       (platform == "Windows" and "/" in current_detection_dir) or \
                       (platform == "Linux" and "\\" in current_detection_dir):
                        detection_dir_entry.delete(0, 'end')
                        detection_dir_entry.insert(0, default_detection_dir)
            except:
                # Widget doesn't exist anymore, that's okay
                pass

        # Save the configuration
        self.config_manager.save_config()

        print(f"Platform changed to {platform}")
        print(f"Base install directory: {default_dir}")
        print(f"Firebird path: {firebird_path}")
        print(f"Jaybird driver path: {jaybird_driver_path}")

    def get_platform_defaults(self, platform):
        """
        Get default paths for a given platform.

        Args:
            platform: Platform name ("Windows" or "Linux")

        Returns:
            dict: Dictionary containing default paths for the platform
        """
        if platform == "Windows":
            return {
                "base_install_dir": "C:\\gkretail",
                "firebird_server_path": "C:\\Program Files\\Firebird\\Firebird_3_0",
                "firebird_driver_path_local": "C:\\gkretail\\Jaybird",
                "file_detection_base_directory": "C:\\gkretail\\stations",
            }
        else:  # Linux
            return {
                "base_install_dir": "/usr/local/gkretail",
                "firebird_server_path": "/opt/firebird",
                "firebird_driver_path_local": "/usr/local/gkretail/Jaybird",
                "file_detection_base_directory": "/usr/local/gkretail/stations",
            }

    def is_path_compatible_with_platform(self, path, platform):
        """
        Check if a path is compatible with the given platform.

        Args:
            path: The path to check
            platform: Platform name ("Windows" or "Linux")

        Returns:
            bool: True if compatible, False otherwise
        """
        if not path:
            return False

        if platform == "Windows":
            # Windows paths should use backslashes
            return "\\" in path and "/" not in path
        else:  # Linux
            # Linux paths should use forward slashes
            return "/" in path and "\\" not in path
