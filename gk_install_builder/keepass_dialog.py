"""Reusable KeePass authentication dialog for retrieving passwords from KeeServer"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from pleasant_password_client import PleasantPasswordClient


class KeePassDialog:
    """
    Reusable KeePass authentication dialog that can retrieve passwords from KeeServer.
    
    Usage:
        dialog = KeePassDialog(parent_window, target_entry, base_url_callback)
        dialog.open()
    """
    
    def __init__(self, parent, target_entry, base_url_callback):
        """
        Initialize KeePass dialog
        
        Args:
            parent: Parent window
            target_entry: Entry widget where password will be inserted
            base_url_callback: Function that returns the base URL string for auto-detection
        """
        self.parent = parent
        self.target_entry = target_entry
        self.base_url_callback = base_url_callback
        
    def open(self):
        """Open the KeePass authentication dialog"""
        from gk_install_builder.main import GKInstallBuilder
        
        # Create dialog
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("KeePass Authentication")
        dialog.geometry("500x550")
        dialog.transient(self.parent)
        
        dialog.update_idletasks()
        dialog.deiconify()
        dialog.wait_visibility()
        dialog.lift()
        dialog.focus_force()
        
        # Center
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - 250
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - 275
        dialog.geometry(f"+{x}+{y}")
        
        dialog.grab_set()
        
        def on_dialog_close():
            try:
                if hasattr(dialog, 'client'):
                    delattr(dialog, 'client')
                if hasattr(dialog, 'folder_contents'):
                    delattr(dialog, 'folder_contents')
            except Exception:
                pass
            finally:
                dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        # Username frame
        username_frame = ctk.CTkFrame(dialog)
        username_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkLabel(username_frame, text="Username:", width=100).pack(side="left")
        username_var = tk.StringVar()
        username_entry = ctk.CTkEntry(username_frame, width=200, textvariable=username_var)
        username_entry.pack(side="left", padx=5)
        
        if GKInstallBuilder.keepass_username:
            username_var.set(GKInstallBuilder.keepass_username)
        
        # Password frame
        password_frame = ctk.CTkFrame(dialog)
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
            dialog,
            text="Remember credentials for this session",
            variable=remember_var
        )
        remember_checkbox.pack(pady=5, padx=20, anchor="w")
        
        # Environment selection frame
        env_frame = ctk.CTkFrame(dialog)
        env_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkLabel(env_frame, text="Environment:", width=100).pack(side="left")
        env_var = tk.StringVar(value="TEST")
        env_combo = ctk.CTkComboBox(env_frame, width=200, variable=env_var, values=["TEST", "PROD"], state="disabled")
        env_combo.pack(side="left", padx=5)
        
        # Connect button (centered)
        connect_btn = ctk.CTkButton(
            dialog,
            text="Connect",
            command=lambda: connect_to_keepass(),
            width=140
        )
        connect_btn.pack(pady=10)
        
        # Status label in its own frame to prevent text overlap
        status_frame = ctk.CTkFrame(dialog)
        status_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        status_var = tk.StringVar(value="Not connected")
        status_label = ctk.CTkLabel(
            status_frame,
            textvariable=status_var,
            wraplength=450,  # Wrap long text
            anchor="center",
            justify="center"
        )
        status_label.pack(fill="x", padx=10, pady=5)
        
        # Detect Projects button (initially disabled)
        detect_projects_btn = ctk.CTkButton(
            dialog,
            text="Detect Projects",
            command=lambda: detect_projects(),
            state="disabled"
        )
        detect_projects_btn.pack(pady=5)
        
        # Get password button (initially disabled)
        get_password_btn = ctk.CTkButton(
            dialog,
            text="Get Password",
            command=lambda: get_password(),
            state="disabled"
        )
        get_password_btn.pack(pady=5)
        
        def connect_to_keepass():
            """Connect to KeePass and auto-detect environment"""
            try:
                status_var.set("Connecting to KeePass server...")
                dialog.update_idletasks()
                
                # Validate inputs
                if not username_var.get().strip():
                    status_var.set("Error: Username cannot be empty")
                    return
                
                if not password_var.get().strip():
                    status_var.set("Error: Password cannot be empty")
                    return
                
                # Get base URL
                base_url = self.base_url_callback()
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
                
                status_var.set("Authenticating...")
                dialog.update_idletasks()
                
                # Create client
                client = PleasantPasswordClient(
                    base_url="https://keeserver.gk.gk-software.com/api/v5/rest/",
                    username=username_var.get(),
                    password=password_var.get()
                )
                
                status_var.set("Authentication successful! Saving settings...")
                dialog.update_idletasks()
                
                # Save credentials if remember is checked
                if remember_var.get():
                    GKInstallBuilder.keepass_client = client
                    GKInstallBuilder.keepass_username = username_var.get()
                    GKInstallBuilder.keepass_password = password_var.get()
                
                # Store client
                dialog.client = client
                
                status_var.set("Connected to KeePass! Auto-detecting environment...")
                dialog.update_idletasks()
                
                # Auto-detect and enable buttons
                detect_projects_btn.configure(state="normal")
                
                status_var.set("Loading...")
                dialog.update_idletasks()
                
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
                dialog.update_idletasks()
                
                folder_contents = client.get_folder_by_id(folder_id, recurse_level=2)
                subfolders = instance.get_subfolders(folder_contents)
                
                # Update environment dropdown
                env_values = [folder['name'] for folder in subfolders] if (subfolders and isinstance(subfolders[0], dict)) else subfolders
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
                dialog.folder_contents = folder_contents
                dialog.selected_project = project_name
                dialog.folder_structure = folder_structure
                
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
            """Show project selection dialog"""
            try:
                client = dialog.client
                status_var.set("Retrieving project list from KeePass...")
                dialog.update_idletasks()
                
                # Get projects
                projects_folder_id = "87300a24-9741-4d24-8a5c-a8b04e0b7049"
                folder_structure = client.get_folder(projects_folder_id)
                
                status_var.set("Processing project folders...")
                dialog.update_idletasks()
                
                # Get direct children
                children = folder_structure.get('Children', [])
                projects = []
                for child in children:
                    projects.append({
                        'name': child.get('Name'),
                        'id': child.get('Id')
                    })
                projects = sorted(projects, key=lambda x: x['name'])
                
                if not projects:
                    status_var.set("No projects found!")
                    return
                
                status_var.set(f"Found {len(projects)} projects. Preparing list...")
                dialog.update_idletasks()
                
                # Create project selection dialog
                proj_dialog = ctk.CTkToplevel(dialog)
                proj_dialog.title("Select Project")
                proj_dialog.geometry("400x600")
                proj_dialog.transient(dialog)
                
                proj_dialog.update_idletasks()
                proj_dialog.deiconify()
                proj_dialog.wait_visibility()
                proj_dialog.lift()
                proj_dialog.focus_force()
                
                # Center
                x = dialog.winfo_x() + (dialog.winfo_width() // 2) - 200
                y = dialog.winfo_y() + (dialog.winfo_height() // 2) - 300
                proj_dialog.geometry(f"+{x}+{y}")
                proj_dialog.grab_set()
                
                proj_dialog.protocol("WM_DELETE_WINDOW", proj_dialog.destroy)
                
                # Label
                ctk.CTkLabel(proj_dialog, text="Available Projects:", font=("Helvetica", 14, "bold")).pack(padx=20, pady=(10, 5))
                
                # Filter
                filter_frame = ctk.CTkFrame(proj_dialog)
                filter_frame.pack(fill="x", padx=20, pady=5)
                
                ctk.CTkLabel(filter_frame, text="Filter:").pack(side="left", padx=(0, 5))
                filter_var = tk.StringVar()
                filter_entry = ctk.CTkEntry(filter_frame, textvariable=filter_var)
                filter_entry.pack(side="left", fill="x", expand=True)
                
                azr_only_var = tk.BooleanVar(value=True)
                azr_checkbox = ctk.CTkCheckBox(filter_frame, text="AZR only", variable=azr_only_var, command=lambda: update_list())
                azr_checkbox.pack(side="left", padx=5)
                
                # Projects frame
                proj_frame = ctk.CTkScrollableFrame(proj_dialog, height=300)
                proj_frame.pack(fill="both", expand=True, padx=20, pady=10)
                
                def update_list(*args):
                    for widget in proj_frame.winfo_children():
                        widget.destroy()
                    
                    filter_text = filter_var.get().lower()
                    azr_only = azr_only_var.get()
                    
                    for project in projects:
                        pname = project['name']
                        if (filter_text in pname.lower()) and (not azr_only or pname.startswith("AZR-")):
                            btn = ctk.CTkButton(proj_frame, text=pname, command=lambda p=project: select_proj(p))
                            btn.pack(fill="x", pady=2)
                
                def select_proj(project):
                    status_var.set(f"Loading {project['name']}...")
                    dialog.update_idletasks()
                    
                    try:
                        folder_contents = client.get_folder_by_id(project['id'], recurse_level=2)
                        
                        from gk_install_builder.main import GKInstallBuilder as Builder
                        instance = Builder(None)
                        subfolders = instance.get_subfolders(folder_contents)
                        
                        env_values = [f['name'] for f in subfolders] if (subfolders and isinstance(subfolders[0], dict)) else subfolders
                        filtered = [e for e in env_values if not e.startswith("INFRA-")]
                        
                        env_combo.configure(values=filtered, state="normal")
                        
                        # Auto-select environment
                        base_url = self.base_url_callback()
                        detected = "TEST"
                        if base_url and "." in base_url:
                            parts = base_url.split(".")
                            if parts[0]:
                                detected = parts[0].upper()
                        
                        if detected in filtered:
                            env_var.set(detected)
                        elif filtered:
                            env_var.set(filtered[0])
                        
                        dialog.folder_contents = folder_contents
                        dialog.selected_project = project['name']
                        
                        get_password_btn.configure(state="normal")
                        proj_dialog.destroy()
                        status_var.set(f"Selected: {project['name']} ({len(filtered)} envs)")
                    except Exception as e:
                        status_var.set(f"Error: {str(e)}")
                
                filter_var.trace_add("write", update_list)
                update_list()
                
            except Exception as e:
                status_var.set(f"Error: {str(e)}")
                import traceback
                traceback.print_exc()
        
        def get_password():
            """Get password from selected project/environment"""
            try:
                base_url = self.base_url_callback()
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
                dialog.update_idletasks()
                
                self.target_entry.delete(0, 'end')
                
                client = dialog.client
                
                if hasattr(dialog, 'folder_contents'):
                    folder_contents = dialog.folder_contents
                    
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
                            
                            self.target_entry.insert(0, password)
                            status_var.set(f"Success! Password retrieved for {environment}")
                            dialog.after(1500, on_dialog_close)
                            return
                
                status_var.set("Error: Could not retrieve password")
            
            except Exception as e:
                status_var.set(f"Error: {str(e)}")
                import traceback
                traceback.print_exc()
