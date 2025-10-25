import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk

class EnvironmentManager:
    """Manager for multi-environment configuration"""
    
    def __init__(self, parent, config_manager, app_instance=None):
        self.parent = parent
        self.config_manager = config_manager
        self.app_instance = app_instance
        self.window = None
        self.environments_listbox = None
        self.selected_index = None
        
    def open_manager(self):
        """Open the Environment Manager dialog"""
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
        
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("Environment Manager - Multi-Tenancy Support")
        self.window.geometry("900x600")
        
        # Make it modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.window.winfo_screenheight() // 2) - (600 // 2)
        self.window.geometry(f"+{x}+{y}")
        
        # Main container
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Environment Manager",
            font=("Helvetica", 18, "bold")
        )
        title_label.pack(pady=(0, 5))
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            main_frame,
            text="Define multiple environments with different credentials and settings.\nScripts will automatically select the correct environment.",
            font=("Helvetica", 11),
            text_color="gray"
        )
        subtitle_label.pack(pady=(0, 15))
        
        # Content area - split into list and details
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill="both", expand=True, pady=5)
        
        # Left side - Environment list
        list_frame = ctk.CTkFrame(content_frame)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        list_label = ctk.CTkLabel(
            list_frame,
            text="Environments",
            font=("Helvetica", 14, "bold")
        )
        list_label.pack(pady=(5, 5))
        
        # Listbox for environments
        self.environments_listbox = tk.Listbox(
            list_frame,
            font=("Helvetica", 11),
            bg="#2b2b2b",
            fg="white",
            selectbackground="#1f538d",
            selectforeground="white",
            relief="flat",
            borderwidth=0
        )
        self.environments_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.environments_listbox.bind("<<ListboxSelect>>", self._on_environment_select)
        
        # Load environments into listbox
        self._refresh_environment_list()
        
        # Buttons under list
        list_buttons_frame = ctk.CTkFrame(list_frame)
        list_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        add_btn = ctk.CTkButton(
            list_buttons_frame,
            text="Add",
            width=80,
            command=self._add_environment
        )
        add_btn.pack(side="left", padx=2)
        
        edit_btn = ctk.CTkButton(
            list_buttons_frame,
            text="Edit",
            width=80,
            command=self._edit_environment
        )
        edit_btn.pack(side="left", padx=2)
        
        clone_btn = ctk.CTkButton(
            list_buttons_frame,
            text="Clone (Multi-Tenancy)",
            width=150,
            command=self._clone_environment,
            fg_color="#2b5f8f",
            hover_color="#1a4060"
        )
        clone_btn.pack(side="left", padx=2)
        
        delete_btn = ctk.CTkButton(
            list_buttons_frame,
            text="Delete",
            width=80,
            command=self._delete_environment,
            fg_color="#8f2b2b",
            hover_color="#601a1a"
        )
        delete_btn.pack(side="left", padx=2)
        
        # Right side - Environment details
        self.details_frame = ctk.CTkScrollableFrame(content_frame, width=400)
        self.details_frame.pack(side="right", fill="both", expand=False, padx=(5, 0))
        
        details_label = ctk.CTkLabel(
            self.details_frame,
            text="Environment Details",
            font=("Helvetica", 14, "bold")
        )
        details_label.pack(pady=(5, 10))
        
        # Show initial message
        self._show_details_placeholder()
        
        # Close button at bottom
        close_btn = ctk.CTkButton(
            main_frame,
            text="Close",
            width=100,
            command=self.window.destroy
        )
        close_btn.pack(pady=(10, 0))
    
    def _refresh_environment_list(self):
        """Refresh the environments listbox"""
        self.environments_listbox.delete(0, tk.END)
        environments = self.config_manager.get_environments()
        
        for env in environments:
            alias = env.get("alias", "")
            name = env.get("name", "")
            base_url = env.get("base_url", "")
            display = f"{alias:10} | {name:20} | {base_url}"
            self.environments_listbox.insert(tk.END, display)
    
    def _on_environment_select(self, event):
        """Handle environment selection"""
        selection = self.environments_listbox.curselection()
        if selection:
            self.selected_index = selection[0]
            self._show_environment_details(self.selected_index)
    
    def _show_details_placeholder(self):
        """Show placeholder when no environment is selected"""
        # Clear previous widgets
        for widget in self.details_frame.winfo_children():
            if widget != self.details_frame.winfo_children()[0]:  # Keep the title
                widget.destroy()
        
        placeholder = ctk.CTkLabel(
            self.details_frame,
            text="Select an environment to view details\nor click 'Add' to create a new one.",
            text_color="gray",
            font=("Helvetica", 11)
        )
        placeholder.pack(expand=True, pady=50)
    
    def _show_environment_details(self, index):
        """Show details of selected environment"""
        environments = self.config_manager.get_environments()
        if index >= len(environments):
            return
        
        env = environments[index]
        
        # Clear previous widgets
        for widget in self.details_frame.winfo_children():
            if widget != self.details_frame.winfo_children()[0]:  # Keep the title
                widget.destroy()
        
        # Display environment details
        fields = [
            ("Alias", env.get("alias", "")),
            ("Name", env.get("name", "")),
            ("Base URL", env.get("base_url", "")),
            ("Tenant ID", env.get("tenant_id", "001") if not env.get("use_default_tenant", False) else "Using default"),
            ("OAuth2 Password", "•" * 12 if env.get("launchpad_oauth2") else "Not set"),
            ("EH Username", env.get("eh_launchpad_username", "")),
            ("EH Password", "•" * 12 if env.get("eh_launchpad_password") else "Not set"),
        ]
        
        for label, value in fields:
            field_frame = ctk.CTkFrame(self.details_frame)
            field_frame.pack(fill="x", pady=5, padx=10)
            
            lbl = ctk.CTkLabel(
                field_frame,
                text=f"{label}:",
                font=("Helvetica", 11, "bold"),
                width=120,
                anchor="w"
            )
            lbl.pack(side="left", padx=(0, 10))
            
            val = ctk.CTkLabel(
                field_frame,
                text=str(value),
                font=("Helvetica", 11),
                anchor="w"
            )
            val.pack(side="left", fill="x", expand=True)
    
    def _add_environment(self):
        """Open dialog to add new environment"""
        self._open_environment_dialog(mode="add")
    
    def _edit_environment(self):
        """Open dialog to edit selected environment"""
        if self.selected_index is None:
            messagebox.showwarning("No Selection", "Please select an environment to edit.")
            return
        self._open_environment_dialog(mode="edit", index=self.selected_index)
    
    def _clone_environment(self):
        """Clone the selected environment for multi-tenancy"""
        if self.selected_index is None:
            messagebox.showwarning("No Selection", "Please select an environment to clone.")
            return
        
        if self.config_manager.clone_environment(self.selected_index):
            messagebox.showinfo("Success", "Environment cloned successfully!\n\nThe clone has '-COPY' appended to its alias and an incremented tenant ID.\n\nPlease edit it to set the correct values.")
            self._refresh_environment_list()
            # Select the newly cloned environment
            self.environments_listbox.selection_clear(0, tk.END)
            self.environments_listbox.selection_set(tk.END)
            self._on_environment_select(None)
        else:
            messagebox.showerror("Error", "Failed to clone environment.")
    
    def _delete_environment(self):
        """Delete the selected environment"""
        if self.selected_index is None:
            messagebox.showwarning("No Selection", "Please select an environment to delete.")
            return
        
        environments = self.config_manager.get_environments()
        env = environments[self.selected_index]
        
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete environment '{env.get('name')}'?\n\nThis action cannot be undone."
        )
        
        if result:
            if self.config_manager.delete_environment(self.selected_index):
                messagebox.showinfo("Success", "Environment deleted successfully.")
                self.selected_index = None
                self._refresh_environment_list()
                self._show_details_placeholder()
            else:
                messagebox.showerror("Error", "Failed to delete environment.")
    
    def _open_environment_dialog(self, mode="add", index=None):
        """Open dialog to add or edit environment
        
        Args:
            mode: 'add' or 'edit'
            index: Index of environment to edit (only for edit mode)
        """
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Add Environment" if mode == "add" else "Edit Environment")
        dialog.geometry("500x700")
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (700 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Get existing data if editing
        env_data = {}
        if mode == "edit" and index is not None:
            environments = self.config_manager.get_environments()
            if index < len(environments):
                env_data = environments[index].copy()
        
        # Main frame
        main_frame = ctk.CTkScrollableFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(
            main_frame,
            text="Environment Configuration",
            font=("Helvetica", 16, "bold")
        )
        title.pack(pady=(0, 20))
        
        # Form fields
        entries = {}
        
        # Alias
        alias_frame = ctk.CTkFrame(main_frame)
        alias_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(alias_frame, text="Alias (e.g., P, DEV, Q-001):", width=200, anchor="w").pack(side="left")
        alias_entry = ctk.CTkEntry(alias_frame, width=250)
        alias_entry.pack(side="left", padx=10)
        alias_entry.insert(0, env_data.get("alias", ""))
        entries["alias"] = alias_entry
        
        # Name
        name_frame = ctk.CTkFrame(main_frame)
        name_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(name_frame, text="Name:", width=200, anchor="w").pack(side="left")
        name_entry = ctk.CTkEntry(name_frame, width=250)
        name_entry.pack(side="left", padx=10)
        name_entry.insert(0, env_data.get("name", ""))
        entries["name"] = name_entry
        
        # Base URL
        base_url_frame = ctk.CTkFrame(main_frame)
        base_url_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(base_url_frame, text="Base URL:", width=200, anchor="w").pack(side="left")
        base_url_entry = ctk.CTkEntry(base_url_frame, width=250)
        base_url_entry.pack(side="left", padx=10)
        base_url_entry.insert(0, env_data.get("base_url", ""))
        entries["base_url"] = base_url_entry
        
        # Use default tenant checkbox
        use_default_var = tk.BooleanVar(value=env_data.get("use_default_tenant", True))
        
        tenant_checkbox_frame = ctk.CTkFrame(main_frame)
        tenant_checkbox_frame.pack(fill="x", pady=10)
        tenant_checkbox = ctk.CTkCheckBox(
            tenant_checkbox_frame,
            text="Use default Tenant ID from main config",
            variable=use_default_var,
            command=lambda: tenant_entry.configure(state="disabled" if use_default_var.get() else "normal")
        )
        tenant_checkbox.pack(anchor="w")
        
        # Tenant ID
        tenant_frame = ctk.CTkFrame(main_frame)
        tenant_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(tenant_frame, text="Tenant ID:", width=200, anchor="w").pack(side="left")
        tenant_entry = ctk.CTkEntry(tenant_frame, width=250)
        tenant_entry.pack(side="left", padx=10)
        tenant_entry.insert(0, env_data.get("tenant_id", "001"))
        tenant_entry.configure(state="disabled" if use_default_var.get() else "normal")
        entries["tenant_id"] = tenant_entry
        
        # Separator
        ctk.CTkLabel(main_frame, text="", height=10).pack()
        ctk.CTkLabel(main_frame, text="Credentials", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        # OAuth2 Password
        oauth_frame = ctk.CTkFrame(main_frame)
        oauth_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(oauth_frame, text="Launchpad OAuth2:", width=200, anchor="w").pack(side="left")
        oauth_entry = ctk.CTkEntry(oauth_frame, width=250, show="*")
        oauth_entry.pack(side="left", padx=10)
        oauth_entry.insert(0, env_data.get("launchpad_oauth2", ""))
        entries["launchpad_oauth2"] = oauth_entry
        
        # Add KeeServer key button (always visible)
        def open_keepass_for_environment():
            """Open full KeePass dialog to get OAuth2 password"""
            from gk_install_builder.pleasant_password_client import PleasantPasswordClient
            from gk_install_builder.main import GKInstallBuilder
            import requests
            import json
            
            # Create dialog
            kp_dialog = ctk.CTkToplevel(dialog)
            kp_dialog.title("KeePass Authentication")
            kp_dialog.geometry("500x550")
            kp_dialog.transient(dialog)
            
            kp_dialog.update_idletasks()
            kp_dialog.deiconify()
            kp_dialog.wait_visibility()
            kp_dialog.lift()
            kp_dialog.focus_force()
            
            # Center
            x = dialog.winfo_x() + (dialog.winfo_width() // 2) - (500 // 2)
            y = dialog.winfo_y() + (dialog.winfo_height() // 2) - (550 // 2)
            kp_dialog.geometry(f"+{x}+{y}")
            
            kp_dialog.grab_set()
            
            def on_kp_dialog_close():
                try:
                    if hasattr(kp_dialog, 'client'):
                        delattr(kp_dialog, 'client')
                    if hasattr(kp_dialog, 'folder_contents'):
                        delattr(kp_dialog, 'folder_contents')
                except Exception:
                    pass
                finally:
                    kp_dialog.destroy()
            
            kp_dialog.protocol("WM_DELETE_WINDOW", on_kp_dialog_close)
            
            # Username frame
            username_frame = ctk.CTkFrame(kp_dialog)
            username_frame.pack(pady=10, fill="x", padx=20)
            
            ctk.CTkLabel(username_frame, text="Username:", width=100).pack(side="left")
            username_var = tk.StringVar()
            username_entry = ctk.CTkEntry(username_frame, width=200, textvariable=username_var)
            username_entry.pack(side="left", padx=5)
            
            if GKInstallBuilder.keepass_username:
                username_var.set(GKInstallBuilder.keepass_username)
            
            # Password frame
            password_frame = ctk.CTkFrame(kp_dialog)
            password_frame.pack(pady=10, fill="x", padx=20)
            
            ctk.CTkLabel(password_frame, text="Password:", width=100).pack(side="left")
            password_var = tk.StringVar()
            password_entry = ctk.CTkEntry(password_frame, width=200, textvariable=password_var, show="*")
            password_entry.pack(side="left", padx=5)
            
            if GKInstallBuilder.keepass_password:
                password_var.set(GKInstallBuilder.keepass_password)
            
            # Remember checkbox
            remember_var = tk.BooleanVar(value=True)
            remember_checkbox = ctk.CTkCheckBox(
                kp_dialog,
                text="Remember credentials for this session",
                variable=remember_var
            )
            remember_checkbox.pack(pady=5, padx=20, anchor="w")
            
            # Environment selection frame
            env_frame = ctk.CTkFrame(kp_dialog)
            env_frame.pack(pady=10, fill="x", padx=20)
            
            ctk.CTkLabel(env_frame, text="Environment:", width=100).pack(side="left")
            env_var = tk.StringVar(value="TEST")
            env_combo = ctk.CTkComboBox(env_frame, width=200, variable=env_var, values=["TEST", "PROD"], state="disabled")
            env_combo.pack(side="left", padx=5)
            
            # Connect button frame
            connect_frame = ctk.CTkFrame(kp_dialog)
            connect_frame.pack(pady=10, fill="x", padx=20)
            
            connect_btn = ctk.CTkButton(
                connect_frame,
                text="Connect",
                command=lambda: connect_to_keepass()
            )
            connect_btn.pack(side="left", padx=10)
            
            # Status label
            status_var = tk.StringVar(value="Not connected")
            status_label = ctk.CTkLabel(connect_frame, textvariable=status_var)
            status_label.pack(side="left", padx=10)
            
            # Detect Projects button (initially disabled)
            detect_projects_btn = ctk.CTkButton(
                kp_dialog,
                text="Detect Projects",
                command=lambda: detect_projects(),
                state="disabled"
            )
            detect_projects_btn.pack(pady=5)
            
            # Get password button (initially disabled)
            get_password_btn = ctk.CTkButton(
                kp_dialog,
                text="Get Password",
                command=lambda: get_password(),
                state="disabled"
            )
            get_password_btn.pack(pady=5)
            
            def connect_to_keepass():
                """Connect to KeePass and auto-detect environment"""
                try:
                    status_var.set("Connecting to KeePass server...")
                    kp_dialog.update_idletasks()
                    status_var.set("Connecting...")
                    kp_dialog.update_idletasks()
                    
                    # Validate inputs
                    if not username_var.get().strip():
                        status_var.set("Error: Username cannot be empty")
                        return
                    
                    if not password_var.get().strip():
                        status_var.set("Error: Password cannot be empty")
                        return
                    
                    # Get base URL
                    base_url = entries["base_url"].get().strip()
                    if not base_url:
                        status_var.set("Error: Please enter Base URL first")
                        return
                    
                    # Auto-detect project and environment
                    project_name = "AZR-CSE"
                    detected_env = "TEST"
                    
                    if "." in base_url:
                        parts = base_url.split(".")
                        if parts[0]:
                            detected_env = parts[0].upper()
                        if len(parts) >= 2 and parts[1]:
                            detected_project = parts[1].upper()
                            project_name = f"AZR-{detected_project}"
                    
                    status_var.set(f"Authenticating...")
                    kp_dialog.update_idletasks()
                    
                    # Create client
                    client = PleasantPasswordClient(
                        base_url="https://keeserver.gk.gk-software.com/api/v5/rest/",
                        username=username_var.get(),
                        password=password_var.get()
                    )
                    
                    status_var.set("Authentication successful! Saving settings...")
                    kp_dialog.update_idletasks()
                    
                    # Save credentials if remember is checked
                    if remember_var.get():
                        GKInstallBuilder.keepass_client = client
                        GKInstallBuilder.keepass_username = username_var.get()
                        GKInstallBuilder.keepass_password = password_var.get()
                    
                    # Store client
                    kp_dialog.client = client
                    
                    status_var.set("Connected to KeePass! Auto-detecting environment...")
                    kp_dialog.update_idletasks()
                    
                    # Auto-detect and enable buttons
                    detect_projects_btn.configure(state="normal")
                    
                    status_var.set(f"Loading...")
                    kp_dialog.update_idletasks()
                    
                    # Get project folder
                    projects_folder_id = "87300a24-9741-4d24-8a5c-a8b04e0b7049"
                    folder_structure = client.get_folder(projects_folder_id)
                    
                    # Find project
                    from gk_install_builder.main import GKInstallBuilder as Builder
                    instance = Builder(None)
                    folder_id = instance.find_folder_id_by_name(folder_structure, project_name)
                    
                    if not folder_id:
                        status_var.set(f"Folder '{project_name}' not found! Click 'Detect Projects' to choose manually.")
                        return
                    
                    # Get environments
                    status_var.set("Processing...")
                    kp_dialog.update_idletasks()
                    
                    folder_contents = client.get_folder_by_id(folder_id, recurse_level=2)
                    subfolders = instance.get_subfolders(folder_contents)
                    
                    # Update environment dropdown
                    env_values = [folder['name'] for folder in subfolders] if isinstance(subfolders[0], dict) else subfolders
                    filtered_env_values = [env for env in env_values if not env.startswith("INFRA-")]
                    
                    env_combo.configure(values=filtered_env_values)
                    
                    # Check if detected environment exists
                    detected_env_exists = detected_env in filtered_env_values
                    
                    if filtered_env_values:
                        if detected_env_exists:
                            env_var.set(detected_env)
                        else:
                            env_var.set(filtered_env_values[0])
                    
                    # Store data
                    kp_dialog.folder_contents = folder_contents
                    kp_dialog.selected_project = project_name
                    kp_dialog.folder_structure = folder_structure
                    
                    # Update status
                    status_var.set(f"Environment Autodetected - {project_name} - {env_var.get()}")
                    
                    # Enable controls
                    env_combo.configure(state="normal")
                    get_password_btn.configure(state="normal")
                
                except Exception as e:
                    status_var.set(f"Error: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            def detect_projects():
                """Show all available projects"""
                try:
                    client = kp_dialog.client
                    status_var.set("Retrieving project list...")
                    kp_dialog.update_idletasks()
                    
                    # Get projects
                    projects_folder_id = "87300a24-9741-4d24-8a5c-a8b04e0b7049"
                    folder_structure = client.get_folder(projects_folder_id)
                    
                    print(f"DEBUG: Folder structure type: {type(folder_structure)}")
                    if isinstance(folder_structure, dict):
                        print(f"DEBUG: Folder keys: {list(folder_structure.keys())}")
                        print(f"DEBUG: Folder name: {folder_structure.get('Name')}")
                        children = folder_structure.get('Children', [])
                        print(f"DEBUG: Number of direct children: {len(children)}")
                        if children:
                            print(f"DEBUG: First child names: {[c.get('Name') for c in children[:5]]}")
                    
                    # Don't use get_subfolders for Projects folder - it has wrapper detection logic
                    # that doesn't apply here. Just get direct children.
                    projects = []
                    for child in children:
                        projects.append({
                            'name': child.get('Name'),
                            'id': child.get('Id')
                        })
                    projects = sorted(projects, key=lambda x: x['name'])
                    
                    print(f"DEBUG: Projects found: {len(projects)}")
                    if projects:
                        print(f"DEBUG: First few projects: {[p.get('name') for p in projects[:5]]}")
                    
                    if not projects:
                        status_var.set("No projects found!")
                        return
                    
                    status_var.set(f"Found {len(projects)} projects")
                    
                    # Simple selection - just enable environment selection
                    get_password_btn.configure(state="normal")
                    
                except Exception as e:
                    status_var.set(f"Error: {str(e)}")
            
            def get_password():
                """Get password from selected project/environment"""
                try:
                    base_url = entries["base_url"].get().strip()
                    if not base_url:
                        status_var.set("Error: Please enter Base URL")
                        return
                    
                    # Auto-detect project
                    project_name = "AZR-CSE"
                    if "." in base_url:
                        parts = base_url.split(".")
                        if len(parts) >= 2 and parts[1]:
                            detected_project = parts[1].upper()
                            project_name = f"AZR-{detected_project}"
                    
                    environment = env_var.get()
                    
                    status_var.set("Retrieving password...")
                    kp_dialog.update_idletasks()
                    
                    oauth_entry.delete(0, 'end')
                    
                    client = kp_dialog.client
                    
                    if hasattr(kp_dialog, 'folder_contents'):
                        folder_contents = kp_dialog.folder_contents
                        
                        from gk_install_builder.main import GKInstallBuilder as Builder
                        instance = Builder(None)
                        
                        # Find environment
                        env_folder = None
                        for folder in instance.get_subfolders(folder_contents):
                            if isinstance(folder, dict) and folder.get('name') == environment:
                                env_folder = folder
                                break
                        
                        if env_folder:
                            env_id = env_folder['id'] if isinstance(env_folder, dict) else env_folder
                            env_structure = client.get_folder_by_id(env_id, recurse_level=2)
                            
                            entry = instance.find_basic_auth_password_entry(env_structure)
                            
                            if entry and isinstance(entry, dict) and 'Id' in entry:
                                password_url = f"credentials/{entry['Id']}/password"
                                password = client._make_request('GET', password_url)
                                
                                oauth_entry.insert(0, password)
                                status_var.set(f"Success! Password retrieved for {environment}")
                                kp_dialog.after(1500, on_kp_dialog_close)
                                return
                    
                    status_var.set("Error: Could not retrieve password")
                
                except Exception as e:
                    status_var.set(f"Error: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        # Add key button
        kee_btn = ctk.CTkButton(
            oauth_frame,
            text="🔑",
            width=40,
            command=open_keepass_for_environment
        )
        kee_btn.pack(side="left", padx=5)
        
        # EH Username
        eh_user_frame = ctk.CTkFrame(main_frame)
        eh_user_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(eh_user_frame, text="EH/Launchpad Username:", width=200, anchor="w").pack(side="left")
        eh_user_entry = ctk.CTkEntry(eh_user_frame, width=250)
        eh_user_entry.pack(side="left", padx=10)
        eh_user_entry.insert(0, env_data.get("eh_launchpad_username", ""))
        entries["eh_launchpad_username"] = eh_user_entry
        
        # EH Password
        eh_pass_frame = ctk.CTkFrame(main_frame)
        eh_pass_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(eh_pass_frame, text="EH/Launchpad Password:", width=200, anchor="w").pack(side="left")
        eh_pass_entry = ctk.CTkEntry(eh_pass_frame, width=250, show="*")
        eh_pass_entry.pack(side="left", padx=10)
        eh_pass_entry.insert(0, env_data.get("eh_launchpad_password", ""))
        entries["eh_launchpad_password"] = eh_pass_entry
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=20)
        
        def save_environment():
            # Validate
            if not entries["alias"].get().strip():
                messagebox.showerror("Validation Error", "Alias is required.")
                return
            if not entries["name"].get().strip():
                messagebox.showerror("Validation Error", "Name is required.")
                return
            if not entries["base_url"].get().strip():
                messagebox.showerror("Validation Error", "Base URL is required.")
                return
            
            # Create environment object
            new_env = {
                "alias": entries["alias"].get().strip(),
                "name": entries["name"].get().strip(),
                "base_url": entries["base_url"].get().strip(),
                "use_default_tenant": use_default_var.get(),
                "tenant_id": entries["tenant_id"].get().strip() if not use_default_var.get() else "",
                "launchpad_oauth2": entries["launchpad_oauth2"].get(),
                "eh_launchpad_username": entries["eh_launchpad_username"].get(),
                "eh_launchpad_password": entries["eh_launchpad_password"].get()
            }
            
            # Save
            if mode == "add":
                self.config_manager.add_environment(new_env)
                messagebox.showinfo("Success", "Environment added successfully.")
            else:
                self.config_manager.update_environment(index, new_env)
                messagebox.showinfo("Success", "Environment updated successfully.")
            
            # Refresh list
            self._refresh_environment_list()
            dialog.destroy()
        
        save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            width=100,
            command=save_environment
        )
        save_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            command=dialog.destroy,
            fg_color="gray",
            hover_color="darkgray"
        )
        cancel_btn.pack(side="left", padx=5)
