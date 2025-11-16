"""
Auto-fill functionality for Store-Install-Builder
Automatically populates configuration fields based on the base URL
"""
import os


class AutoFillManager:
    """Manages automatic configuration based on base URL"""

    def __init__(self, config_manager):
        """
        Initialize AutoFillManager.

        Args:
            config_manager: ConfigManager instance for reading/writing configuration
        """
        self.config_manager = config_manager

    def auto_fill_based_on_url(self, base_url, platform_var=None):
        """
        Auto-fill fields based on the base URL.

        Args:
            base_url: The base URL to extract information from
            platform_var: Optional platform variable (tk.StringVar or similar) to get platform

        Returns:
            bool: True if auto-fill was successful
        """
        # Skip if URL is empty
        if not base_url:
            return False

        print(f"Auto-filling based on URL: {base_url}")

        # Get current platform
        if platform_var and hasattr(platform_var, 'get'):
            platform = platform_var.get()
        else:
            platform = self.config_manager.config.get("platform", "Windows")

        # Determine default installation directory based on platform
        default_install_dir = "/usr/local/gkretail" if platform == "Linux" else "C:\\gkretail"

        # Extract project name from URL as the part after the first dot
        extracted_project_name = ""
        project_code = ""
        if "." in base_url:
            parts = base_url.split(".")
            if len(parts) > 1:
                # Check if this is a product URL (e.g., dev.cloud4retail.co, qa.cloud4retail.co)
                if parts[1].lower() == "cloud4retail":
                    # Product URLs - use the first part as the project name and default to GKR
                    extracted_project_name = parts[0].upper()
                    project_code = "GKR"
                    print(f"Detected product URL, using GKR prefix for system types")
                    print(f"Project name from product URL: {extracted_project_name}")
                else:
                    # Customer URLs like dev.cse.cloud4retail.co
                    # Extract the part after the first dot (index 1) and uppercase it for project code
                    project_code = parts[1].upper()
                    # Use this for prefix detection in system types
                    print(f"Detected project code from URL: {project_code}")

                    # Also use it as the project name if not set
                    extracted_project_name = project_code

        # Auto-fill system types based on the detected project code
        if project_code:
            # Use the detected project code for system types
            pos_system_type = f"{project_code}-OPOS-CLOUD"
            wdm_system_type = f"{project_code}-wdm"
            # FLOWSERVICE always uses GKR prefix (exception)
            flow_service_system_type = "GKR-FLOWSERVICE-CLOUD"
            lpa_service_system_type = f"{project_code}-lps-lpa"
            storehub_service_system_type = f"{project_code}-sh-cloud"

            print(f"Setting system types based on detected project code: {project_code}")
        else:
            # Default to CSE system types if no project code detected
            pos_system_type = "CSE-OPOS-CLOUD"
            wdm_system_type = "CSE-wdm"
            flow_service_system_type = "GKR-FLOWSERVICE-CLOUD"
            lpa_service_system_type = "CSE-lps-lpa"
            storehub_service_system_type = "CSE-sh-cloud"

        # Update project name entry if it's empty and we extracted a valid name
        if extracted_project_name and self.config_manager.get_entry("project_name") and not self.config_manager.get_entry("project_name").get():
            self.config_manager.update_entry_value("project_name", extracted_project_name)
            print(f"Auto-filled project name: {extracted_project_name}")

        # Get current project name (either from entry or use the extracted name as fallback)
        project_name = self.config_manager.get_entry("project_name").get() if self.config_manager.get_entry("project_name") else extracted_project_name

        # Create a structured output directory using the original pattern: ProjectName/base_url
        if self.config_manager.get_entry("output_dir"):
            if project_name:
                # Use the project name and full URL to create the directory structure
                output_dir = os.path.join(project_name, base_url)
            else:
                # Fallback to a simple directory if project name is missing
                output_dir = "generated_scripts"

            self.config_manager.update_entry_value("output_dir", output_dir)
            print(f"Auto-filled output directory: {output_dir}")

        # Auto-fill certificate path
        if self.config_manager.get_entry("certificate_path"):
            # Use a certificate path inside the output directory
            if project_name:
                cert_path = os.path.join(project_name, base_url, "certificate.p12")
            else:
                # Fallback if project name is not set
                cert_path = f"generated_scripts/{base_url}_certificate.p12"

            self.config_manager.update_entry_value("certificate_path", cert_path)
            print(f"Auto-filled certificate path: {cert_path}")

        # Update system types
        if self.config_manager.get_entry("pos_system_type"):
            self.config_manager.update_entry_value("pos_system_type", pos_system_type)
            print(f"Auto-filled POS system type: {pos_system_type}")

        if self.config_manager.get_entry("wdm_system_type"):
            self.config_manager.update_entry_value("wdm_system_type", wdm_system_type)
            print(f"Auto-filled WDM system type: {wdm_system_type}")

        if self.config_manager.get_entry("flow_service_system_type"):
            self.config_manager.update_entry_value("flow_service_system_type", flow_service_system_type)
            print(f"Auto-filled Flow Service system type: {flow_service_system_type}")

        if self.config_manager.get_entry("lpa_service_system_type"):
            self.config_manager.update_entry_value("lpa_service_system_type", lpa_service_system_type)
            print(f"Auto-filled LPA Service system type: {lpa_service_system_type}")

        if self.config_manager.get_entry("storehub_service_system_type"):
            self.config_manager.update_entry_value("storehub_service_system_type", storehub_service_system_type)
            print(f"Auto-filled StoreHub Service system type: {storehub_service_system_type}")

        # Set the base install directory only if other values were updated
        base_dir_entry = self.config_manager.get_entry("base_install_dir")
        current = base_dir_entry.get() if base_dir_entry else self.config_manager.config.get("base_install_dir", "")
        if not current or (platform == "Windows" and "/" in current) or (platform == "Linux" and "\\" in current):
            if base_dir_entry:
                base_dir_entry.delete(0, 'end')
                base_dir_entry.insert(0, default_install_dir)
            self.config_manager.config["base_install_dir"] = default_install_dir
            print(f"Auto-filled base install directory: {default_install_dir}")

        # Only set these other defaults if their fields are empty
        if self.config_manager.get_entry("username") and not self.config_manager.get_entry("username").get():
            self.config_manager.update_entry_value("username", "launchpad")
        if self.config_manager.get_entry("eh_launchpad_username") and not self.config_manager.get_entry("eh_launchpad_username").get():
            self.config_manager.update_entry_value("eh_launchpad_username", "1001")
        if self.config_manager.get_entry("ssl_password") and not self.config_manager.get_entry("ssl_password").get():
            self.config_manager.update_entry_value("ssl_password", "changeit")

        return True

    def extract_project_code(self, base_url):
        """
        Extract project code from base URL.

        Args:
            base_url: The base URL

        Returns:
            str: The project code (e.g., "CSE", "GKR")
        """
        if not base_url or "." not in base_url:
            return "GKR"

        parts = base_url.split(".")
        if len(parts) > 1:
            if parts[1].lower() == "cloud4retail":
                return "GKR"  # Product URL
            else:
                return parts[1].upper()  # Customer URL
        return "GKR"
