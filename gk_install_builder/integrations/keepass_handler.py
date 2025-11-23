"""KeePass Handler for Store-Install-Builder

This module manages KeePass integration for retrieving credentials from Pleasant Password Server.
"""

from tkinter import messagebox
try:
    from gk_install_builder.pleasant_password_client import PleasantPasswordClient
except ImportError:
    from pleasant_password_client import PleasantPasswordClient


class KeePassHandler:
    """Handler for KeePass/Pleasant Password integration"""

    # Class variables to store KeePass client and credentials
    keepass_client = None
    keepass_credentials = {}
    keepass_username = None
    keepass_password = None

    def __init__(self, parent_window, config_manager):
        """Initialize the KeePass Handler

        Args:
            parent_window: The parent Tkinter window
            config_manager: The ConfigManager instance
        """
        self.root = parent_window
        self.config_manager = config_manager

        # Initialize KeePass variables from class variables
        self.keepass_client = KeePassHandler.keepass_client
        self.keepass_username = KeePassHandler.keepass_username
        self.keepass_password = KeePassHandler.keepass_password

        # References to password entry widgets (will be set by parent app)
        self.basic_auth_password_entry = None
        self.webdav_admin_password_entry = None

        # Reference to keepass_button (will be set by parent app if it exists)
        self.keepass_button = None

    def set_password_entries(self, basic_auth_entry=None, webdav_admin_entry=None):
        """Set references to password entry widgets

        Args:
            basic_auth_entry: The basic auth password entry widget
            webdav_admin_entry: The webdav admin password entry widget
        """
        if basic_auth_entry:
            self.basic_auth_password_entry = basic_auth_entry
        if webdav_admin_entry:
            self.webdav_admin_password_entry = webdav_admin_entry

    def set_keepass_button(self, button):
        """Set reference to the KeePass button widget

        Args:
            button: The KeePass button widget
        """
        self.keepass_button = button

    def update_keepass_button(self):
        """Update the KeePass button state based on whether credentials are stored"""
        # Skip if the keepass_button doesn't exist
        if not hasattr(self, 'keepass_button') or not self.keepass_button:
            return

        if self.keepass_client and self.keepass_username and self.keepass_password:
            # We have credentials, show the disconnect button
            self.keepass_button.configure(
                text="Disconnect from KeePass",
                command=self.clear_keepass_credentials
            )
        else:
            # No credentials, show the connect button
            self.keepass_button.configure(
                text="Connect to KeePass",
                command=self.get_basic_auth_password_from_keepass
            )

    def get_basic_auth_password_from_keepass(self, target_entry=None, password_type="basic_auth"):
        """Get password from KeePass

        Args:
            target_entry: The target entry widget to populate (optional)
            password_type: The type of password to retrieve ("basic_auth" or "webdav_admin")
        """
        from gk_install_builder.keepass_dialog import KeePassDialog

        # If no target entry is specified, use the appropriate password entry based on type
        if target_entry is None:
            if password_type == "basic_auth":
                target_entry = self.basic_auth_password_entry
            elif password_type == "webdav_admin":
                target_entry = self.webdav_admin_password_entry

        # Create callback to get base URL from config
        def get_base_url():
            return self.config_manager.config.get("base_url", "")

        # Create and open the KeePass dialog
        keepass_dialog = KeePassDialog(
            parent=self.root,
            target_entry=target_entry,
            base_url_callback=get_base_url
        )
        keepass_dialog.open()

    def find_basic_auth_password_entry(self, folder_structure):
        """Find Basic Auth password entry in KeePass folder structure

        Args:
            folder_structure: The KeePass folder structure dictionary

        Returns:
            The credential entry dictionary if found, None otherwise
        """
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

                # Dynamically build the target credential names based on environment
                if env_name:
                    # Support both naming formats: dashes and underscores
                    target_cred_name_dash = f"{env_name}-LAUNCHPAD-OAUTH-BA-PASSWORD"
                    target_cred_name_underscore = f"{env_name}_LAUNCHPAD_OAUTH_BA_PASSWORD"

                    # First priority: exact match for dash format in APP subfolder
                    if cred_name == target_cred_name_dash and "APP" in current_path:
                        print(f"FOUND TARGET ENTRY (dash format): {target_cred_name_dash} in {current_path}")
                        target_entry = cred
                        return cred

                    # First priority: exact match for underscore format in APP subfolder
                    if cred_name == target_cred_name_underscore and "APP" in current_path:
                        print(f"FOUND TARGET ENTRY (underscore format): {target_cred_name_underscore} in {current_path}")
                        target_entry = cred
                        return cred

                    # Second priority: exact match for dash format anywhere
                    if cred_name == target_cred_name_dash:
                        print(f"FOUND EXACT MATCH (dash format): {target_cred_name_dash} in {current_path}")
                        found_entries.append({
                            'priority': 1,
                            'entry': cred,
                            'path': current_path,
                            'reason': f'Exact match for {target_cred_name_dash} (dash format)'
                        })

                    # Second priority: exact match for underscore format anywhere
                    if cred_name == target_cred_name_underscore:
                        print(f"FOUND EXACT MATCH (underscore format): {target_cred_name_underscore} in {current_path}")
                        found_entries.append({
                            'priority': 1,
                            'entry': cred,
                            'path': current_path,
                            'reason': f'Exact match for {target_cred_name_underscore} (underscore format)'
                        })

            # Third priority: entries with LAUNCHPAD-OAUTH-BA-PASSWORD (dash format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'LAUNCHPAD-OAUTH-BA-PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains LAUNCHPAD-OAUTH-BA-PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 2,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains LAUNCHPAD-OAUTH-BA-PASSWORD: {cred_name} (dash format)'
                    })

            # Third priority: entries with LAUNCHPAD_OAUTH_BA_PASSWORD (underscore format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'LAUNCHPAD_OAUTH_BA_PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains LAUNCHPAD_OAUTH_BA_PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 2,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains LAUNCHPAD_OAUTH_BA_PASSWORD: {cred_name} (underscore format)'
                    })

            # Fourth priority: entries with BA-PASSWORD (dash format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'BA-PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains BA-PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 3,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains BA-PASSWORD: {cred_name} (dash format)'
                    })

            # Fourth priority: entries with BA_PASSWORD (underscore format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'BA_PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains BA_PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 3,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains BA_PASSWORD: {cred_name} (underscore format)'
                    })

            # Fifth priority: entries with rare format LAUNCHPAD_OAUTH
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if cred_name == 'LAUNCHPAD_OAUTH':
                    print(f"FOUND MATCH: Rare format LAUNCHPAD_OAUTH in {current_path}")
                    found_entries.append({
                        'priority': 4,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Rare format: LAUNCHPAD_OAUTH'
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
            print(f"\nNo exact match for {env_name}-LAUNCHPAD-OAUTH-BA-PASSWORD or {env_name}_LAUNCHPAD_OAUTH_BA_PASSWORD found in APP subfolder.")
            print(f"Using best match: {best_match['reason']} in {best_match['path']}")
            return best_match['entry']

        # If no result found, print all credentials for debugging
        if not result and not found_entries:
            print("\nAll credentials found during search:")
            for cred in all_credentials:
                print(f"  - {cred['path']}: {cred['name']} (ID: {cred['id']})")

        return result

    def find_webdav_admin_password_entry(self, folder_structure):
        """Find Webdav Admin password entry in KeePass folder structure

        Args:
            folder_structure: The KeePass folder structure dictionary

        Returns:
            The credential entry dictionary if found, None otherwise
        """
        print("\nSearching for Webdav Admin password entry...")
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

                # Dynamically build the target credential names based on environment
                if env_name:
                    # Support both naming formats: dashes and underscores
                    target_cred_name_dash = f"{env_name}-DSG-WEBDAV-ADMIN-PASSWORD"
                    target_cred_name_underscore = f"{env_name}_DSG_WEBDAV_ADMIN_PASSWORD"

                    # First priority: exact match for dash format in APP subfolder
                    if cred_name == target_cred_name_dash and "APP" in current_path:
                        print(f"FOUND TARGET ENTRY (dash format): {target_cred_name_dash} in {current_path}")
                        target_entry = cred
                        return cred

                    # First priority: exact match for underscore format in APP subfolder
                    if cred_name == target_cred_name_underscore and "APP" in current_path:
                        print(f"FOUND TARGET ENTRY (underscore format): {target_cred_name_underscore} in {current_path}")
                        target_entry = cred
                        return cred

                    # Second priority: exact match for dash format anywhere
                    if cred_name == target_cred_name_dash:
                        print(f"FOUND EXACT MATCH (dash format): {target_cred_name_dash} in {current_path}")
                        found_entries.append({
                            'priority': 1,
                            'entry': cred,
                            'path': current_path,
                            'reason': f'Exact match for {target_cred_name_dash} (dash format)'
                        })

                    # Second priority: exact match for underscore format anywhere
                    if cred_name == target_cred_name_underscore:
                        print(f"FOUND EXACT MATCH (underscore format): {target_cred_name_underscore} in {current_path}")
                        found_entries.append({
                            'priority': 1,
                            'entry': cred,
                            'path': current_path,
                            'reason': f'Exact match for {target_cred_name_underscore} (underscore format)'
                        })

            # Third priority: entries with DSG-WEBDAV-ADMIN-PASSWORD (dash format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'DSG-WEBDAV-ADMIN-PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains DSG-WEBDAV-ADMIN-PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 2,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains DSG-WEBDAV-ADMIN-PASSWORD: {cred_name} (dash format)'
                    })

            # Third priority: entries with DSG_WEBDAV_ADMIN_PASSWORD (underscore format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'DSG_WEBDAV_ADMIN_PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains DSG_WEBDAV_ADMIN_PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 2,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains DSG_WEBDAV_ADMIN_PASSWORD: {cred_name} (underscore format)'
                    })

            # Fourth priority: entries with WEBDAV-ADMIN-PASSWORD (dash format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'WEBDAV-ADMIN-PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains WEBDAV-ADMIN-PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 3,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains WEBDAV-ADMIN-PASSWORD: {cred_name} (dash format)'
                    })

            # Fourth priority: entries with WEBDAV_ADMIN_PASSWORD (underscore format)
            for cred in credentials:
                cred_name = cred.get('Name', '')
                if 'WEBDAV_ADMIN_PASSWORD' in cred_name:
                    print(f"FOUND MATCH: Contains WEBDAV_ADMIN_PASSWORD: {cred_name} in {current_path}")
                    found_entries.append({
                        'priority': 3,
                        'entry': cred,
                        'path': current_path,
                        'reason': f'Contains WEBDAV_ADMIN_PASSWORD: {cred_name} (underscore format)'
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
            print(f"\nNo exact match for {env_name}-DSG-WEBDAV-ADMIN-PASSWORD or {env_name}_DSG_WEBDAV_ADMIN_PASSWORD found in APP subfolder.")
            print(f"Using best match: {best_match['reason']} in {best_match['path']}")
            return best_match['entry']

        # If no result found, print all credentials for debugging
        if not result and not found_entries:
            print("\nAll credentials found during search:")
            for cred in all_credentials:
                print(f"  - {cred['path']}: {cred['name']} (ID: {cred['id']})")

        return result

    def find_folder_id_by_name(self, folder_structure, search_name):
        """Find folder ID by name in the folder structure

        Args:
            folder_structure: The KeePass folder structure dictionary
            search_name: The name of the folder to search for

        Returns:
            The folder ID if found, None otherwise
        """
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
        """Get subfolders from the folder structure

        Args:
            folder_structure: The KeePass folder structure dictionary

        Returns:
            List of subfolder dictionaries with 'name', 'id', and optionally 'parent_wrapper'
        """
        folders = []
        if isinstance(folder_structure, dict):
            children = folder_structure.get('Children', [])

            # Check if we have wrapper folders (like DEV-OPOS-01, PRD-OPOS-01)
            # If so, flatten by looking at their children instead
            has_wrapper_folders = False
            for child in children:
                child_name = child.get('Name', '')
                # Detect wrapper patterns: contains OPOS or similar patterns
                if '-OPOS-' in child_name or child_name.endswith('-01') or child_name.endswith('-02'):
                    has_wrapper_folders = True
                    break

            if has_wrapper_folders:
                # Flatten: get children of wrapper folders
                for wrapper in children:
                    wrapper_children = wrapper.get('Children', [])
                    for child in wrapper_children:
                        folders.append({
                            'name': child.get('Name'),
                            'id': child.get('Id'),
                            'parent_wrapper': wrapper.get('Name')  # Keep track of which wrapper this came from
                        })
            else:
                # Normal behavior: direct children
                for child in children:
                    folders.append({
                        'name': child.get('Name'),
                        'id': child.get('Id')
                    })
        return sorted(folders, key=lambda x: x['name'])

    def print_all_credentials(self, folder_structure, path=""):
        """Print all credentials in the folder structure for debugging

        Args:
            folder_structure: The KeePass folder structure dictionary
            path: The current path in the folder structure (for recursion)
        """
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

    def clear_keepass_credentials(self):
        """Clear stored KeePass credentials"""
        KeePassHandler.keepass_client = None
        KeePassHandler.keepass_username = None
        KeePassHandler.keepass_password = None

        # Update instance variables
        self.keepass_client = None
        self.keepass_username = None
        self.keepass_password = None

        # Update the button state if button exists
        if hasattr(self, 'keepass_button') and self.keepass_button:
            self.update_keepass_button()

        messagebox.showinfo("KeePass Credentials", "KeePass credentials have been cleared.")
