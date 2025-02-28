import requests
from typing import Optional, Dict, Any
import json
from urllib.parse import urljoin

class PleasantPasswordClient:
    def __init__(self, base_url: str, username: str, password: str):
        """
        Initialize the Pleasant Password Server API client
        
        Args:
            base_url: Base URL of the Pleasant Password Server (e.g. https://keeserver.example.com/api/v5/rest/)
            username: Username for authentication
            password: Password for authentication
        """
        self.base_url = base_url.rstrip('/') + '/'
        self.server_url = self.base_url.split('/api/')[0]  # Extract server base URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        # Get OAuth token
        self._authenticate(username, password)

    def _authenticate(self, username: str, password: str):
        """Authenticate using OAuth2"""
        auth_url = f"{self.server_url}/OAuth2/Token"
        
        data = {
            'grant_type': 'password',
            'username': username,
            'password': password
        }
        
        try:
            response = requests.post(
                auth_url, 
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()
            
            # Extract token from response
            token_data = response.json()
            access_token = token_data['access_token']
            
            # Update session headers with bearer token
            self.session.headers.update({
                'Authorization': f"Bearer {access_token}"
            })
        except requests.exceptions.RequestException as e:
            print(f"Authentication failed: {e}")
            # Check for 2FA requirement
            if response.status_code == 400:
                otp_required = response.headers.get('X-Pleasant-OTP')
                if otp_required == 'required':
                    otp_provider = response.headers.get('X-Pleasant-OTP-Provider')
                    print(f"Two-factor authentication required (Provider: {otp_provider})")
            raise

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to the API"""
        url = urljoin(self.base_url, endpoint)
        
        # Debug print for API call
        print(f"\nDebug - Making API call:")
        print(f"Method: {method}")
        print(f"URL: {url}")
        if data:
            print(f"Data: {json.dumps(data, indent=2)}")
        
        try:
            response = self.session.request(method, url, json=data)
            response.raise_for_status()
            
            # Debug print for response
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            raise

    # Entries (Credentials) endpoints
    def get_entries(self):
        """Get all entries"""
        return self._make_request('GET', 'entries')

    def get_entry(self, entry_id: int):
        """Get a specific entry by ID"""
        return self._make_request('GET', f'entries/{entry_id}')

    def create_entry(self, entry_data: Dict):
        """Create a new entry"""
        return self._make_request('POST', 'entries', data=entry_data)

    def update_entry(self, entry_id: int, entry_data: Dict):
        """Update an existing entry"""
        return self._make_request('PUT', f'entries/{entry_id}', data=entry_data)

    def patch_entry(self, entry_id: int, patch_data: Dict):
        """Partially update an entry"""
        return self._make_request('PATCH', f'entries/{entry_id}', data=patch_data)

    def get_entry_by_id(self, entry_id: str):
        """
        Get a specific entry by its ID
        Args:
            entry_id: GUID of the entry
        """
        return self._make_request('GET', f'entries/{entry_id}')

    def get_entry_password(self, entry_id: str):
        """
        Get the password for a specific entry
        Args:
            entry_id: GUID of the entry
        Returns:
            String: The password
        """
        return self._make_request('GET', f'credentials/{entry_id}/password')

    # Folders endpoints
    def get_folders(self):
        """Get all folders"""
        return self._make_request('GET', 'folders')

    def get_folder(self, folder_id: int):
        """Get a specific folder by ID"""
        return self._make_request('GET', f'folders/{folder_id}')

    def create_folder(self, folder_data: Dict):
        """Create a new folder"""
        return self._make_request('POST', 'folders', data=folder_data)

    def get_root_folder(self):
        """Get the root folder"""
        return self._make_request('GET', 'folders/root')

    def get_folder_by_id(self, folder_id: str, recurse_level: int = 1):
        """
        Get a specific folder and its contents by ID with recursion level
        Args:
            folder_id: GUID of the folder
            recurse_level: How deep to recurse the folder tree (default: 1)
        """
        return self._make_request('GET', f'folders/{folder_id}?recurseLevel={recurse_level}')

    # User Access endpoints
    def get_user_access(self):
        """Get user access information"""
        return self._make_request('GET', 'useraccess')

    # Server Info
    def get_server_info(self):
        """Get server information"""
        return self._make_request('GET', 'serverinfo')

    def find_folder_by_name(self, folder_name: str):
        """
        Find a folder by its name and return its details
        Args:
            folder_name: Name of the folder to find (e.g., 'AZR-CSE')
        """
        folders = self.get_folders()
        
        def search_folder(items):
            """Recursively search through folder structure"""
            for item in items:
                if item.get('name') == folder_name:
                    return item
                if 'items' in item:
                    result = search_folder(item['items'])
                    if result:
                        return result
            return None
        
        return search_folder(folders) 