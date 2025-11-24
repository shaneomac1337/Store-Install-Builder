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

from gk_install_builder.utils.version_sorting import get_latest_version, sort_versions


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
        """Test the Employee Hub Function Pack API to fetch default versions"""
        try:
            # Show loading message
            print("[TEST API] Creating loading dialog...")
            loading_dialog = ctk.CTkToplevel(self.root)
            loading_dialog.title("Testing Function Pack API")
            loading_dialog.geometry("500x300")
            loading_dialog.transient(self.root)

            # Center the dialog
            loading_dialog.update_idletasks()
            x = (loading_dialog.winfo_screenwidth() // 2) - (500 // 2)
            y = (loading_dialog.winfo_screenheight() // 2) - (300 // 2)
            loading_dialog.geometry(f"500x300+{x}+{y}")

            loading_label = ctk.CTkLabel(loading_dialog, text="Testing Employee Hub Function Pack API...\nGenerating authentication token...\nPlease wait...", wraplength=450)
            loading_label.pack(expand=True, padx=20, pady=20)

            # Add a progress info label
            progress_label = ctk.CTkLabel(loading_dialog, text="Step 1 of 3: Authenticating...", text_color="gray")
            progress_label.pack(padx=20, pady=10)

            # Update the dialog and ensure it's visible before grabbing
            loading_dialog.update()
            loading_dialog.deiconify()  # Ensure window is visible

            # Try to grab focus with error handling for Linux compatibility
            try:
                loading_dialog.grab_set()
            except Exception as e:
                print(f"[TEST API] Warning: Could not grab window focus: {e}")
                # Continue without grab - dialog will still work

            # Try to generate token using credentials from config
            print("[TEST API] Step 1 of 3: Generating authentication token...")
            bearer_token = self._generate_api_token(base_url, loading_label, loading_dialog)

            if not bearer_token:
                print("[TEST API] ERROR: Failed to generate bearer token!")
                loading_dialog.destroy()
                messagebox.showerror("Authentication Failed",
                    "Could not generate authentication token.\n\n"
                    "Please ensure all Security Configuration details are filled in first and that you can reach the Employee Hub itself.\n\n"
                    "1. Basic Auth Password (launchpad_oauth2)\n"
                    "2. Form Password (eh_launchpad_password)\n"
                    "3. Base URL is correct\n"
                    "4. Network connectivity\n\n"
                    "Go to the Security Configuration tab and complete all required fields.")
                return

            # Update loading message
            loading_label.configure(text="Testing Employee Hub Function Pack API...\nFetching component versions (FP scope)...\nPlease wait...")
            loading_dialog.update()

            # Prepare headers for API requests
            headers = {
                "authorization": f"Bearer {bearer_token}",
                "gk-tenant-id": "001",
                "Referer": f"https://{base_url}/employee-hub/app/index.html"
            }
            print(f"[TEST API] Headers prepared (token length: {len(bearer_token)})")
            print(f"[TEST API] Authorization: Bearer {bearer_token[:50]}...")  # Log truncated for security
            print(f"[TEST API] Referer: {headers['Referer']}")

            # Initialize versions tracking
            versions = {
                "POS": {"value": None, "source": None},
                "WDM": {"value": None, "source": None},
                "FLOW-SERVICE": {"value": None, "source": None},
                "LPA-SERVICE": {"value": None, "source": None},
                "STOREHUB-SERVICE": {"value": None, "source": None}
            }

            # Step 1: Try FP scope first (modified/customized versions)
            # Try multiple URL patterns as fallback
            fp_urls = [
                f"https://{base_url}/api/employee-hub-service/services/rest/v1/properties?scope=FP&referenceId=platform",
                f"https://{base_url}/employee-hub-service/services/rest/v1/properties?scope=FP&referenceId=platform"
            ]

            print(f"[TEST API] Step 2 of 3: Fetching FP scope...")
            fp_response = None
            fp_success = False

            for i, fp_api_url in enumerate(fp_urls):
                print(f"[TEST API] Trying FP URL pattern {i+1}/{len(fp_urls)}: {fp_api_url}")

                try:
                    print(f"[TEST API] Making FP scope request...")
                    print(f"[TEST API] Request method: GET")
                    if i == 0:  # Only print headers on first attempt to avoid spam
                        print(f"[TEST API] Request headers:")
                        for key, value in headers.items():
                            if key == "authorization":
                                print(f"[TEST API]   {key}: Bearer {value.replace('Bearer ', '')[:50]}...")
                            else:
                                print(f"[TEST API]   {key}: {value}")

                    fp_response = requests.get(fp_api_url, headers=headers, timeout=30, verify=False)
                    print(f"[TEST API] FP response status code: {fp_response.status_code}")

                    if fp_response.status_code == 200:
                        print(f"[TEST API] ✅ FP URL pattern {i+1} worked!")
                        print(f"[TEST API] FP response headers: {dict(fp_response.headers)}")
                        print(f"[TEST API] FP response length: {len(fp_response.text)} bytes")
                        fp_success = True
                        break
                    else:
                        print(f"[TEST API] ❌ FP URL pattern {i+1} returned {fp_response.status_code}")
                        if i == len(fp_urls) - 1:  # Last attempt, show response
                            print(f"[TEST API] Response text: {fp_response.text[:500]}")
                        continue

                except Exception as e:
                    print(f"[TEST API] ❌ FP URL pattern {i+1} failed: {e}")
                    if i == len(fp_urls) - 1:  # Last attempt failed
                        print(f"[TEST API] All FP URL patterns failed")
                    continue

            if fp_success:
                try:
                    print(f"[TEST API] Full response body:")
                    print(f"[TEST API] {fp_response.text}")
                    print(f"[TEST API] " + "-"*80)

                    fp_data = fp_response.json()
                    print(f"[TEST API] FP response parsed successfully (items: {len(fp_data) if isinstance(fp_data, list) else 'N/A'})")
                    print(f"[TEST API] FP response type: {type(fp_data)}")
                    print(f"[TEST API] Raw FP data (first 500 chars): {str(fp_data)[:500]}")

                    # Parse FP scope results
                    if isinstance(fp_data, list):
                        for idx, property_item in enumerate(fp_data):
                            prop_id = property_item.get("propertyId", "")
                            value = property_item.get("value", "")
                            print(f"[TEST API]   Item {idx}: propertyId='{prop_id}', value='{value}'")

                            # POS: try Update_Version first, fallback to Version
                            if prop_id in ["POSClient_Update_Version", "POSClient_Version"] and value:
                                if versions["POS"]["value"] is None or prop_id == "POSClient_Update_Version":
                                    versions["POS"] = {"value": value, "source": "FP (Modified)"}
                                    print(f"[TEST API]     -> Matched POS ({prop_id}): {value}")
                            # WDM: try Version first, fallback to Update_Version
                            elif prop_id in ["WDM_Version", "WDM_Update_Version"] and value:
                                if versions["WDM"]["value"] is None or prop_id == "WDM_Version":
                                    versions["WDM"] = {"value": value, "source": "FP (Modified)"}
                                    print(f"[TEST API]     -> Matched WDM ({prop_id}): {value}")
                            # FlowService: try Version first, fallback to Update_Version
                            elif prop_id in ["FlowService_Version", "FlowService_Update_Version"] and value:
                                if versions["FLOW-SERVICE"]["value"] is None or prop_id == "FlowService_Version":
                                    versions["FLOW-SERVICE"] = {"value": value, "source": "FP (Modified)"}
                                    print(f"[TEST API]     -> Matched FlowService ({prop_id}): {value}")
                            # LPA: try Version first, fallback to Update_Version
                            elif prop_id in ["LPA_Version", "LPA_Update_Version"] and value:
                                if versions["LPA-SERVICE"]["value"] is None or prop_id == "LPA_Version":
                                    versions["LPA-SERVICE"] = {"value": value, "source": "FP (Modified)"}
                                    print(f"[TEST API]     -> Matched LPA ({prop_id}): {value}")
                            # StoreHub: try Update_Version first, fallback to Version
                            elif prop_id in ["SH_Update_Version", "StoreHub_Version"] and value:
                                if versions["STOREHUB-SERVICE"]["value"] is None or prop_id == "SH_Update_Version":
                                    versions["STOREHUB-SERVICE"] = {"value": value, "source": "FP (Modified)"}
                                    print(f"[TEST API]     -> Matched StoreHub ({prop_id}): {value}")
                    else:
                        print(f"[TEST API] ERROR: FP response is not a list, it's a {type(fp_data)}")
                except Exception as json_err:
                    print(f"[TEST API] ERROR parsing FP JSON: {json_err}")
                    print(f"[TEST API] Response text: {fp_response.text[:500]}")

            # Step 2: For components not found in FP, try FPD scope (default versions)
            missing_components = [comp for comp, data in versions.items() if data["value"] is None]

            if missing_components:
                loading_label.configure(text="Testing Employee Hub Function Pack API...\nFetching missing components (FPD scope)...\nPlease wait...")
                loading_dialog.update()

                # Try multiple URL patterns for FPD as well
                fpd_urls = [
                    f"https://{base_url}/api/employee-hub-service/services/rest/v1/properties?scope=FPD&referenceId=platform",
                    f"https://{base_url}/employee-hub-service/services/rest/v1/properties?scope=FPD&referenceId=platform"
                ]

                fpd_response = None
                fpd_success = False

                for i, fpd_api_url in enumerate(fpd_urls):
                    print(f"[TEST API] Trying FPD URL pattern {i+1}/{len(fpd_urls)}: {fpd_api_url}")

                    try:
                        fpd_response = requests.get(fpd_api_url, headers=headers, timeout=30, verify=False)
                        print(f"[TEST API] FPD response status code: {fpd_response.status_code}")

                        if fpd_response.status_code == 200:
                            print(f"[TEST API] ✅ FPD URL pattern {i+1} worked!")
                            fpd_success = True
                            break
                        else:
                            print(f"[TEST API] ❌ FPD URL pattern {i+1} returned {fpd_response.status_code}")
                            continue
                    except Exception as e:
                        print(f"[TEST API] ❌ FPD URL pattern {i+1} failed: {e}")
                        continue

                if fpd_success:
                    try:
                        fpd_data = fpd_response.json()

                        # Parse FPD scope results for missing components only
                        for property_item in fpd_data:
                            prop_id = property_item.get("propertyId", "")
                            value = property_item.get("value", "")

                            # POS: try Update_Version first, fallback to Version
                            if prop_id in ["POSClient_Update_Version", "POSClient_Version"] and value and versions["POS"]["value"] is None:
                                versions["POS"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched POS ({prop_id}): {value}")
                            # WDM: try Version first, fallback to Update_Version
                            elif prop_id in ["WDM_Version", "WDM_Update_Version"] and value and versions["WDM"]["value"] is None:
                                versions["WDM"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched WDM ({prop_id}): {value}")
                            # FlowService: try Version first, fallback to Update_Version
                            elif prop_id in ["FlowService_Version", "FlowService_Update_Version"] and value and versions["FLOW-SERVICE"]["value"] is None:
                                versions["FLOW-SERVICE"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched FlowService ({prop_id}): {value}")
                            # LPA: try Version first, fallback to Update_Version
                            elif prop_id in ["LPA_Version", "LPA_Update_Version"] and value and versions["LPA-SERVICE"]["value"] is None:
                                versions["LPA-SERVICE"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched LPA ({prop_id}): {value}")
                            # StoreHub: try Update_Version first, fallback to Version
                            elif prop_id in ["SH_Update_Version", "StoreHub_Version"] and value and versions["STOREHUB-SERVICE"]["value"] is None:
                                versions["STOREHUB-SERVICE"] = {"value": value, "source": "FPD (Default)"}
                                print(f"[TEST API]     -> Matched StoreHub ({prop_id}): {value}")
                    except Exception as e:
                        print(f"Warning: FPD scope request failed: {e}")

            loading_dialog.destroy()

            # Show results with status and source for each component
            print(f"[TEST API] Test complete. Processing results...")
            result_text = "✅ API Test Successful!\n\nComponent Version Status:\n\n"

            found_count = 0
            for component, data in versions.items():
                if data["value"]:
                    result_text += f"✅ {component}: {data['value']} ({data['source']})\n"
                    found_count += 1
                    print(f"[TEST API] ✅ {component}: {data['value']} ({data['source']})")
                else:
                    result_text += f"❌ {component}: Not Found\n"
                    print(f"[TEST API] ❌ {component}: Not Found")

            result_text += f"\n📊 Summary: {found_count}/5 components found"
            result_text += f"\n🔍 Search Strategy: FP scope first, FPD scope for missing components"

            if found_count == 0:
                result_text += "\n\n⚠️ No component versions found in either FP or FPD scope"

            print(f"[TEST API] " + "="*80)
            print(f"[TEST API] SUMMARY: {found_count}/5 components found")
            print(f"[TEST API] " + "="*80)
            messagebox.showinfo("API Test Results", result_text)

        except requests.exceptions.RequestException as e:
            if 'loading_dialog' in locals():
                loading_dialog.destroy()
            messagebox.showerror("API Test Failed",
                f"Network error: {str(e)}\n\n"
                f"Please check your network connection and ensure all Security Configuration details are filled in first.")
        except Exception as e:
            if 'loading_dialog' in locals():
                loading_dialog.destroy()
            messagebox.showerror("API Test Failed",
                f"Error: {str(e)}\n\n"
                f"Please ensure all Security Configuration details are filled in first.")

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
            print(f"[TOKEN GEN] Form data keys: {list(form_data_dict.keys())}")
            print(f"[TOKEN GEN] Form data (encoded): {form_data[:100]}...")

            # Make OAuth token request
            token_url = f"https://{base_url}/auth-service/tenants/001/oauth/token"
            print(f"[TOKEN GEN] Token URL: {token_url}")
            print(f"[TOKEN GEN] Auth header: Basic {auth_b64[:50]}...")

            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            # Update loading message
            loading_label.configure(text="Requesting OAuth token...\nPlease wait...")
            loading_dialog.update()

            print(f"[TOKEN GEN] Sending POST request...")
            response = requests.post(token_url, headers=headers, data=form_data, timeout=30, verify=False)

            print(f"[TOKEN GEN] Token response status: {response.status_code}")
            print(f"[TOKEN GEN] Token response text: {response.text[:500]}")
            print(f"[TOKEN GEN] Token response headers: {dict(response.headers)}")

            if response.status_code == 200:
                try:
                    token_data = response.json()
                    access_token = token_data.get('access_token')
                    if access_token:
                        print(f"[TOKEN GEN] ✅ Token generated successfully (length: {len(access_token)})")
                        return access_token
                    else:
                        print(f"[TOKEN GEN] ERROR: No access_token in response")
                except Exception as e:
                    print(f"[TOKEN GEN] ERROR parsing token response: {e}")
                    pass
            else:
                print(f"[TOKEN GEN] ERROR: Non-200 status code: {response.status_code}")

            print(f"[TOKEN GEN] Returning None - token generation failed")
            return None

        except Exception as e:
            print(f"[TOKEN GEN] EXCEPTION in _generate_api_token: {e}")
            import traceback
            print(f"[TOKEN GEN] Traceback: {traceback.format_exc()}")
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
            print("[CONFIG API] Step 1: Generating authentication token...")
            bearer_token = self._generate_api_token(base_url, loading_label, loading_dialog)

            if not bearer_token:
                print("[CONFIG API] ERROR: Failed to generate bearer token!")
                loading_dialog.destroy()
                messagebox.showerror("Authentication Failed",
                    "Could not generate authentication token.\n\n"
                    "Please ensure all Security Configuration details are filled in first.")
                return

            # Update loading message
            loading_label.configure(text="Testing Config-Service API...\nFetching versions for all components...\nPlease wait...")
            loading_dialog.update()

            # Prepare headers
            headers = {
                "authorization": f"Bearer {bearer_token}",
                "content-type": "application/json"
            }
            print(f"[CONFIG API] Headers prepared (token length: {len(bearer_token)})")

            # Get system types from config
            system_types = {
                "POS": self.config_manager.config.get("pos_system_type", "GKR-OPOS-CLOUD"),
                "WDM": self.config_manager.config.get("wdm_system_type", "CSE-wdm"),
                "FLOW-SERVICE": self.config_manager.config.get("flow_service_system_type", "GKR-FLOWSERVICE-CLOUD"),
                "LPA-SERVICE": self.config_manager.config.get("lpa_service_system_type", "CSE-lps-lpa"),
                "STOREHUB-SERVICE": self.config_manager.config.get("storehub_service_system_type", "CSE-sh-cloud")
            }

            print(f"[CONFIG API] System types: {system_types}")

            # Initialize versions tracking
            versions = {}

            # API URL
            api_url = f"https://{base_url}/api/config/services/rest/infrastructure/v1/versions/search"
            print(f"[CONFIG API] API URL: {api_url}")

            # Fetch versions for each component
            for component, system_name in system_types.items():
                print(f"[CONFIG API] Fetching versions for {component} (systemName: {system_name})...")

                payload = {"systemName": system_name}

                try:
                    response = requests.post(api_url, headers=headers, json=payload, timeout=30, verify=False)
                    print(f"[CONFIG API] {component} response status: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        version_list = data.get("versionNameList", [])

                        if version_list:
                            # Sort versions and get the latest (highest) version
                            sorted_versions = sort_versions(version_list, descending=True)
                            latest_version = get_latest_version(version_list)

                            if latest_version:
                                versions[component] = {"value": latest_version, "source": "Config-Service", "all_versions": sorted_versions}
                                print(f"[CONFIG API] ✅ {component}: {latest_version} (available: {len(version_list)} versions, sorted)")
                            else:
                                # Fallback to first in sorted list if get_latest_version returns None
                                versions[component] = {"value": sorted_versions[0], "source": "Config-Service", "all_versions": sorted_versions}
                                print(f"[CONFIG API] ✅ {component}: {sorted_versions[0]} (available: {len(version_list)} versions, fallback)")
                        else:
                            versions[component] = {"value": None, "source": None, "all_versions": []}
                            print(f"[CONFIG API] ❌ {component}: No versions found")
                    else:
                        print(f"[CONFIG API] ❌ {component} returned status {response.status_code}: {response.text[:200]}")
                        versions[component] = {"value": None, "source": None, "all_versions": []}

                except Exception as e:
                    print(f"[CONFIG API] ❌ {component} request failed: {e}")
                    versions[component] = {"value": None, "source": None, "all_versions": []}

            loading_dialog.destroy()

            # Show results
            print(f"[CONFIG API] Test complete. Processing results...")
            result_text = "✅ Config-Service API Test Successful!\n\nComponent Version Status:\n\n"

            found_count = 0
            for component, data in versions.items():
                if data["value"]:
                    all_versions_str = ", ".join(data.get("all_versions", [])[:3])  # Show first 3 versions
                    if len(data.get("all_versions", [])) > 3:
                        all_versions_str += "..."
                    result_text += f"✅ {component}: {data['value']}\n   Available: {all_versions_str}\n\n"
                    found_count += 1
                    print(f"[CONFIG API] ✅ {component}: {data['value']}")
                else:
                    result_text += f"❌ {component}: Not Found\n\n"
                    print(f"[CONFIG API] ❌ {component}: Not Found")

            result_text += f"📊 Summary: {found_count}/5 components found"
            result_text += f"\n🔍 API: Config-Service (versions/search)"

            if found_count == 0:
                result_text += "\n\n⚠️ No component versions found"

            print(f"[CONFIG API] " + "="*80)
            print(f"[CONFIG API] SUMMARY: {found_count}/5 components found")
            print(f"[CONFIG API] " + "="*80)
            messagebox.showinfo("Config-Service API Test Results", result_text)

        except requests.exceptions.RequestException as e:
            if 'loading_dialog' in locals():
                loading_dialog.destroy()
            messagebox.showerror("API Test Failed",
                f"Network error: {str(e)}\n\n"
                f"Please check your network connection.")
        except Exception as e:
            if 'loading_dialog' in locals():
                loading_dialog.destroy()
            messagebox.showerror("API Test Failed",
                f"Error: {str(e)}\n\n"
                f"Please ensure all configuration details are correct.")
