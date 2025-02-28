import tkinter as tk
from tkinter import ttk, messagebox
from pleasant_password_client import PleasantPasswordClient
import json
from datetime import datetime

class PasswordRetrieverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Pleasant Password Retriever")
        self.root.geometry("600x400")
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Authentication frame
        self.auth_frame = ttk.LabelFrame(self.main_frame, text="Authentication", padding="5")
        self.auth_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(self.auth_frame, text="Username:").grid(row=0, column=0, sticky=tk.W)
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(self.auth_frame, textvariable=self.username_var)
        self.username_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        ttk.Label(self.auth_frame, text="Password:").grid(row=1, column=0, sticky=tk.W)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(self.auth_frame, textvariable=self.password_var, show="*")
        self.password_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))
        
        # Project selection frame
        self.project_frame = ttk.LabelFrame(self.main_frame, text="Project Selection", padding="5")
        self.project_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(self.project_frame, text="Project Name:").grid(row=0, column=0, sticky=tk.W)
        self.project_var = tk.StringVar()
        self.project_entry = ttk.Entry(self.project_frame, textvariable=self.project_var)
        self.project_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.project_entry.insert(0, "AZR-CSE")
        
        # Environment selection
        ttk.Label(self.project_frame, text="Environment:").grid(row=1, column=0, sticky=tk.W)
        self.env_var = tk.StringVar()
        self.env_combo = ttk.Combobox(self.project_frame, textvariable=self.env_var, state="readonly")
        self.env_combo.grid(row=1, column=1, sticky=(tk.W, tk.E))
        
        # Buttons
        self.connect_btn = ttk.Button(self.main_frame, text="Connect", command=self.connect)
        self.connect_btn.grid(row=2, column=0, pady=5)
        
        self.get_password_btn = ttk.Button(self.main_frame, text="Get Password", command=self.get_password, state="disabled")
        self.get_password_btn.grid(row=2, column=1, pady=5)
        
        # Status and output
        self.status_var = tk.StringVar()
        ttk.Label(self.main_frame, textvariable=self.status_var).grid(row=3, column=0, columnspan=2)
        
        self.output_text = tk.Text(self.main_frame, height=10, width=50)
        self.output_text.grid(row=4, column=0, columnspan=2, pady=5)
        
        # Initialize client as None
        self.client = None
        self.folder_structure = None

    def connect(self):
        try:
            self.client = PleasantPasswordClient(
                base_url="https://keeserver.gk.gk-software.com/api/v5/rest/",
                username=self.username_var.get(),
                password=self.password_var.get()
            )
            
            # Get project folder
            projects_folder_id = "87300a24-9741-4d24-8a5c-a8b04e0b7049"
            self.folder_structure = self.client.get_folder(projects_folder_id)
            
            # Find project folder
            folder_id = self.find_folder_id_by_name(self.folder_structure, self.project_var.get())
            if folder_id:
                # Get environments
                folder_contents = self.client.get_folder(folder_id)
                subfolders = self.get_subfolders(folder_contents)
                
                # Update environment dropdown
                self.env_combo['values'] = [folder['name'] for folder in subfolders]
                if self.env_combo['values']:
                    self.env_combo.set(self.env_combo['values'][0])
                
                self.get_password_btn['state'] = 'normal'
                self.status_var.set("Connected successfully!")
            else:
                messagebox.showerror("Error", f"Project {self.project_var.get()} not found!")
        
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {str(e)}")

    def get_password(self):
        try:
            # Get folder structure for selected environment
            folder_id = self.find_folder_id_by_name(self.folder_structure, self.project_var.get())
            folder_contents = self.client.get_folder(folder_id)
            
            # Find selected environment folder
            for subfolder in self.get_subfolders(folder_contents):
                if subfolder['name'] == self.env_var.get():
                    env_folder = subfolder
                    break
            
            # Get full folder structure
            folder_structure = self.client.get_folder_by_id(env_folder['id'], recurse_level=5)
            
            # Find password entry
            launchpad_entry = self.find_launchpad_password_entry(folder_structure)
            if launchpad_entry:
                # Get password
                password = self.client._make_request('GET', f'credentials/{launchpad_entry["Id"]}/password')
                
                # Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"password_{launchpad_entry['Id']}_{timestamp}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(str(password))
                
                # Show in output
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, f"Password saved to: {filename}\n\n")
                self.output_text.insert(tk.END, f"Password:\n{password}")
                
                self.status_var.set("Password retrieved successfully!")
            else:
                messagebox.showerror("Error", "No Launchpad OAuth password entry found!")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get password: {str(e)}")

    # Helper functions from original script
    def find_folder_id_by_name(self, folder_structure, search_name):
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
        folders = []
        if isinstance(folder_structure, dict):
            children = folder_structure.get('Children', [])
            for child in children:
                folders.append({
                    'name': child.get('Name'),
                    'id': child.get('Id')
                })
        return sorted(folders, key=lambda x: x['name'])

    def find_launchpad_password_entry(self, folder_structure):
        if isinstance(folder_structure, dict):
            credentials = folder_structure.get('Credentials', [])
            for cred in credentials:
                if 'LAUNCHPAD-OAUTH' in cred.get('Name', ''):
                    return cred

            children = folder_structure.get('Children', [])
            for child in children:
                result = self.find_launchpad_password_entry(child)
                if result:
                    return result
        return None

def main():
    root = tk.Tk()
    app = PasswordRetrieverGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 