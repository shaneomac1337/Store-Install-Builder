"""
API Integration Client for Store-Install-Builder
Handles OAuth token generation and API testing for version management
"""

import customtkinter as ctk
from tkinter import messagebox
import requests
import base64
import urllib.parse
import json


class APIClient:
    """Client for API integrations (OAuth, Function Pack API, Config-Service API)"""

    def __init__(self, parent_window, config_manager):
        """
        Initialize API Client

        Args:
            parent_window: Parent tkinter window
            config_manager: ConfigManager instance
        """
        self.root = parent_window
        self.config_manager = config_manager

    def test_default_versions_api(self):
        """Test the API to fetch default versions - shows modal to choose method"""
        try:
            # Force save current GUI values to config before testing
            print("\n" + "="*80)
            print("[TEST API] Starting API test...")
            print("="*80)
            print("[TEST API] Forcing config update from GUI fields...")
            self.config_manager.update_config_from_entries()
            self.config_manager.save_config_silent()

            # Get base URL from config
            base_url = self.config_manager.config.get("base_url", "")
            print(f"[TEST API] Retrieved base URL: {base_url}")
            if not base_url:
                print("[TEST API] ERROR: Base URL is empty!")
                messagebox.showerror("Error", "Please configure the Base URL first")
                return

            # Show modal dialog to choose API method
            self._show_api_method_dialog(base_url)

        except Exception as e:
            print(f"[TEST API] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")

    def _show_api_method_dialog(self, base_url):
        """Show modal dialog to choose between API methods"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Choose API Method")
        dialog.geometry("500x250")
        dialog.transient(self.root)

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (250)
        y = (dialog.winfo_screenheight() // 2) - (125)
        dialog.geometry(f"500x250+{x}+{y}")

        # Title label
        title_label = ctk.CTkLabel(dialog, text="Select API Method", font=("Arial", 16, "bold"))
        title_label.pack(pady=20)

        # Description
        desc_label = ctk.CTkLabel(
            dialog,
            text="Choose which API to use for fetching component versions:",
            wraplength=450
        )
        desc_label.pack(pady=10)

        # Buttons frame
        buttons_frame = ctk.CTkFrame(dialog)
        buttons_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Function Pack API button
        fp_button = ctk.CTkButton(
            buttons_frame,
            text="Old Way (Function Pack)\n\nUses Employee Hub Function Pack API\nto fetch versions from FP/FPD scope",
            width=220,
            height=80,
            command=lambda: [dialog.destroy(), self._test_function_pack_api(base_url)]
        )
        fp_button.pack(side="left", padx=10)

        # Config-Service API button
        cs_button = ctk.CTkButton(
            buttons_frame,
            text="New Way (Config-Service)\n\nUses Config-Service API\nto fetch versions by system name",
            width=220,
            height=80,
            command=lambda: [dialog.destroy(), self._test_config_service_api(base_url)]
        )
        cs_button.pack(side="right", padx=10)

        # Make dialog modal
        dialog.grab_set()
        dialog.focus_force()

    def _test_function_pack_api(self, base_url):
        """Test the Function Pack API (old way - FP/FPD scope)"""
        try:
            # Show loading message
            print("[FUNCTION PACK API] Creating loading dialog...")
            loading_dialog = ctk.CTkToplevel(self.root)
            loading_dialog.title("Testing Function Pack API")
            loading_dialog.geometry("500x300")
            loading_dialog.transient(self.root)

            # Center the dialog
            loading_dialog.update_idletasks()
            x = (loading_dialog.winfo_screenwidth() // 2) - (250)
            y = (loading_dialog.winfo_screenheight() // 2) - (150)
            loading_dialog.geometry(f"500x300+{x}+{y}")

            loading_label = ctk.CTkLabel(loading_dialog, text="Testing Function Pack API...\nGenerating authentication token...\nPlease wait...", wraplength=450)
            loading_label.pack(expand=True, padx=20, pady=20)

            # Update the dialog and ensure it's visible
            loading_dialog.update()
            loading_dialog.deiconify()

            # Try to grab focus
            try:
                loading_dialog.grab_set()
            except Exception as e:
                print(f"[FUNCTION PACK API] Warning: Could not grab window focus: {e}")

            # Generate token
            print("[FUNCTION PACK API] Generating OAuth token...")
            bearer_token = self._generate_api_token(base_url, loading_label, loading_dialog)

            if not bearer_token:
                print("[FUNCTION PACK API] ERROR: Failed to generate token")
                loading_dialog.destroy()
                messagebox.showerror(
                    "Authentication Failed",
                    "Could not generate authentication token.\n\n"
                    "Please check your Security Configuration:\n"
                    "- Basic Auth Password (launchpad_oauth2)\n"
                    "- Form Username (eh_launchpad_username)\n"
                    "- Form Password (eh_launchpad_password)"
                )
                return

            print(f"[FUNCTION PACK API] Token generated successfully (first 20 chars): {bearer_token[:20]}...")

            # Update loading message
            loading_label.configure(text="Testing Function Pack API...\nFetching POS version from FP scope...\nPlease wait...")
            loading_dialog.update()

            # Try to generate token using credentials from config
            print("[FUNCTION PACK API] Attempting to fetch POS version from Function Pack API...")

            # Build the Function Pack API URL
            fp_api_url = f"https://{base_url}/employee-hub-service/backend/api/fp/CLOUD-POS/version"
            print(f"[FUNCTION PACK API] Request URL: {fp_api_url}")

            headers = {
                'Authorization': f'Bearer {bearer_token}',
                'Content-Type': 'application/json'
            }

            response = requests.get(fp_api_url, headers=headers, timeout=30, verify=False)
            print(f"[FUNCTION PACK API] Response status: {response.status_code}")

            if response.status_code == 200:
                version_data = response.json()
                version = version_data.get('version', 'N/A')
                print(f"[FUNCTION PACK API] SUCCESS: POS version from FP: {version}")

                # Update loading message with success
                loading_label.configure(text=f"✅ SUCCESS!\n\nFetched POS version from Function Pack API:\n{version}\n\nThe 'Old Way' (Function Pack) is working correctly!")
                loading_dialog.update()

                # Wait a bit before closing
                loading_dialog.after(3000, loading_dialog.destroy)

                messagebox.showinfo(
                    "Function Pack API Test Success",
                    f"Successfully fetched POS version from Function Pack API!\n\n"
                    f"Version: {version}\n\n"
                    f"The 'Old Way' (FP/FPD scope) is working correctly."
                )
            else:
                print(f"[FUNCTION PACK API] ERROR: Unexpected response status: {response.status_code}")
                print(f"[FUNCTION PACK API] Response body: {response.text}")

                loading_dialog.destroy()
                messagebox.showerror(
                    "API Test Failed",
                    f"Function Pack API returned status {response.status_code}\n\n"
                    f"Response: {response.text[:200]}"
                )

        except requests.exceptions.Timeout:
            print("[FUNCTION PACK API] ERROR: Request timed out")
            try:
                loading_dialog.destroy()
            except:
                pass
            messagebox.showerror("Timeout", "Request timed out. Please check your network connection and base URL.")
        except requests.exceptions.RequestException as e:
            print(f"[FUNCTION PACK API] ERROR: Request exception: {e}")
            try:
                loading_dialog.destroy()
            except:
                pass
            messagebox.showerror("Request Error", f"Failed to connect to API:\n\n{str(e)}")
        except Exception as e:
            print(f"[FUNCTION PACK API] ERROR: Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            try:
                loading_dialog.destroy()
            except:
                pass
            messagebox.showerror("Error", f"An unexpected error occurred:\n\n{str(e)}")

    def _generate_api_token(self, base_url, loading_label, loading_dialog):
        """Generate API token using credentials from config"""
        try:
            # Update loading message
            loading_label.configure(text="Generating authentication token...\nUsing credentials from configuration...")
            loading_dialog.update()

            # Get the correct credentials from config
            # Note: These come from the Security Configuration section
            basic_auth_password = self.config_manager.config.get("launchpad_oauth2", "")  # Basic Auth password (for launchpad:password)
            form_username = self.config_manager.config.get("eh_launchpad_username", "")  # Form username (e.g., gk01ag)
            form_password = self.config_manager.config.get("eh_launchpad_password", "")  # Form password (e.g., gk12345)

            print(f"[TOKEN GEN] basic_auth_password present: {bool(basic_auth_password)} (length: {len(basic_auth_password) if basic_auth_password else 0})")
            print(f"[TOKEN GEN] form_username present: {bool(form_username)} (length: {len(form_username) if form_username else 0})")
            print(f"[TOKEN GEN] form_password present: {bool(form_password)} (length: {len(form_password) if form_password else 0})")
            print(f"[TOKEN GEN] Config keys: {list(self.config_manager.config.keys())}")

            if not basic_auth_password or not form_username or not form_password:
                print(f"[TOKEN GEN] ERROR: Missing credentials!")
                print(f"[TOKEN GEN]   launchpad_oauth2: {bool(basic_auth_password)}")
                print(f"[TOKEN GEN]   eh_launchpad_username: {bool(form_username)}")
                print(f"[TOKEN GEN]   eh_launchpad_password: {bool(form_password)}")
                return None

            # Handle both base64 encoded and plain text passwords
            try:
                # Try to decode as base64 first
                basic_auth_password_decoded = base64.b64decode(basic_auth_password).decode('utf-8')
                print(f"[TOKEN GEN] Successfully decoded basic_auth_password from base64")
            except Exception as e:
                # If decoding fails, assume it's already plain text
                print(f"[TOKEN GEN] basic_auth_password appears to be plain text (decode error: {e})")
                basic_auth_password_decoded = basic_auth_password

            try:
                # Try to decode form_password
                form_password_decoded = base64.b64decode(form_password).decode('utf-8')
                print(f"[TOKEN GEN] Successfully decoded form_password from base64")
            except Exception as e:
                print(f"[TOKEN GEN] form_password appears to be plain text (decode error: {e})")
                form_password_decoded = form_password

            # Create Basic Auth header (username is always "launchpad")
            username = "launchpad"
            auth_string = f"{username}:{basic_auth_password_decoded}"
            auth_b64 = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
            print(f"[TOKEN GEN] Basic Auth header created (first 20 chars): {auth_b64[:20]}...")

            # Prepare form data for OAuth token request
            form_data_dict = {
                'username': form_username,
                'password': form_password_decoded,
                'grant_type': 'password'
            }

            # URL encode form data
            encoded_pairs = []
            for key, value in form_data_dict.items():
                encoded_key = urllib.parse.quote_plus(str(key))
                encoded_value = urllib.parse.quote_plus(str(value))
                encoded_pairs.append(f"{encoded_key}={encoded_value}")

            form_data = '&'.join(encoded_pairs)
            print(f"[TOKEN GEN] Form data prepared (keys: {list(form_data_dict.keys())})")

            # Make OAuth token request
            token_url = f"https://{base_url}/auth-service/tenants/001/oauth/token"
            print(f"[TOKEN GEN] Token URL: {token_url}")

            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            print(f"[TOKEN GEN] Making OAuth token request...")
            response = requests.post(token_url, headers=headers, data=form_data, timeout=30, verify=False)

            print(f"[TOKEN GEN] Response status: {response.status_code}")

            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get('access_token')
                if access_token:
                    print(f"[TOKEN GEN] SUCCESS: Token generated (length: {len(access_token)})")
                    return access_token
                else:
                    print(f"[TOKEN GEN] ERROR: No access_token in response")
                    print(f"[TOKEN GEN] Response keys: {list(token_data.keys())}")
                    return None
            else:
                print(f"[TOKEN GEN] ERROR: Token request failed with status {response.status_code}")
                print(f"[TOKEN GEN] Response: {response.text}")
                return None

        except Exception as e:
            print(f"[TOKEN GEN] ERROR: Exception during token generation: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _test_config_service_api(self, base_url):
        """Test the Config-Service API to fetch versions by system name"""
        try:
            # Show loading message
            print("[CONFIG API] Creating loading dialog...")
            loading_dialog = ctk.CTkToplevel(self.root)
            loading_dialog.title("Testing Config-Service API")
            loading_dialog.geometry("500x300")
            loading_dialog.transient(self.root)

            # Center the dialog
            loading_dialog.update_idletasks()
            x = (loading_dialog.winfo_screenwidth() // 2) - (250)
            y = (loading_dialog.winfo_screenheight() // 2) - (150)
            loading_dialog.geometry(f"500x300+{x}+{y}")

            loading_label = ctk.CTkLabel(loading_dialog, text="Testing Config-Service API...\nGenerating authentication token...\nPlease wait...", wraplength=450)
            loading_label.pack(expand=True, padx=20, pady=20)

            # Update the dialog and ensure it's visible
            loading_dialog.update()
            loading_dialog.deiconify()

            # Try to grab focus
            try:
                loading_dialog.grab_set()
            except Exception as e:
                print(f"[CONFIG API] Warning: Could not grab window focus: {e}")

            # Generate token
            print("[CONFIG API] Generating OAuth token...")
            bearer_token = self._generate_api_token(base_url, loading_label, loading_dialog)

            if not bearer_token:
                print("[CONFIG API] ERROR: Failed to generate token")
                loading_dialog.destroy()
                messagebox.showerror(
                    "Authentication Failed",
                    "Could not generate authentication token.\n\n"
                    "Please check your Security Configuration:\n"
                    "- Basic Auth Password (launchpad_oauth2)\n"
                    "- Form Username (eh_launchpad_username)\n"
                    "- Form Password (eh_launchpad_password)"
                )
                return

            print(f"[CONFIG API] Token generated successfully (first 20 chars): {bearer_token[:20]}...")

            # Update loading message
            loading_label.configure(text="Testing Config-Service API...\nFetching POS version by system name...\nPlease wait...")
            loading_dialog.update()

            # Get the POS system type from config
            pos_system_type = self.config_manager.config.get("pos_system_type", "")
            print(f"[CONFIG API] POS system type from config: {pos_system_type}")

            if not pos_system_type:
                print("[CONFIG API] ERROR: No POS system type configured")
                loading_dialog.destroy()
                messagebox.showerror(
                    "Configuration Error",
                    "No POS system type configured.\n\n"
                    "Please configure the POS system type in the main window first."
                )
                return

            # Build the Config-Service API URL
            cs_api_url = f"https://{base_url}/config-service/backend/api/config/version?systemName={pos_system_type}"
            print(f"[CONFIG API] Request URL: {cs_api_url}")

            headers = {
                'Authorization': f'Bearer {bearer_token}',
                'Content-Type': 'application/json'
            }

            response = requests.get(cs_api_url, headers=headers, timeout=30, verify=False)
            print(f"[CONFIG API] Response status: {response.status_code}")

            if response.status_code == 200:
                version_data = response.json()
                version = version_data.get('version', 'N/A')
                print(f"[CONFIG API] SUCCESS: POS version from Config-Service: {version}")

                # Update loading message with success
                loading_label.configure(text=f"✅ SUCCESS!\n\nFetched POS version from Config-Service API:\n{version}\n\nThe 'New Way' (Config-Service) is working correctly!")
                loading_dialog.update()

                # Wait a bit before closing
                loading_dialog.after(3000, loading_dialog.destroy)

                messagebox.showinfo(
                    "Config-Service API Test Success",
                    f"Successfully fetched POS version from Config-Service API!\n\n"
                    f"System Name: {pos_system_type}\n"
                    f"Version: {version}\n\n"
                    f"The 'New Way' (Config-Service) is working correctly."
                )
            else:
                print(f"[CONFIG API] ERROR: Unexpected response status: {response.status_code}")
                print(f"[CONFIG API] Response body: {response.text}")

                loading_dialog.destroy()
                messagebox.showerror(
                    "API Test Failed",
                    f"Config-Service API returned status {response.status_code}\n\n"
                    f"Response: {response.text[:200]}"
                )

        except requests.exceptions.Timeout:
            print("[CONFIG API] ERROR: Request timed out")
            try:
                loading_dialog.destroy()
            except:
                pass
            messagebox.showerror("Timeout", "Request timed out. Please check your network connection and base URL.")
        except requests.exceptions.RequestException as e:
            print(f"[CONFIG API] ERROR: Request exception: {e}")
            try:
                loading_dialog.destroy()
            except:
                pass
            messagebox.showerror("Request Error", f"Failed to connect to API:\n\n{str(e)}")
        except Exception as e:
            print(f"[CONFIG API] ERROR: Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            try:
                loading_dialog.destroy()
            except:
                pass
            messagebox.showerror("Error", f"An unexpected error occurred:\n\n{str(e)}")
