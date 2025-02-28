from pleasant_password_client import PleasantPasswordClient
import getpass
import json
from datetime import datetime

def find_folder_id_by_name(folder_structure, search_name):
    """Find folder ID by name in the folder structure"""
    if isinstance(folder_structure, dict):
        # Check current folder
        if folder_structure.get('Name') == search_name:
            return folder_structure.get('Id')
            
        # Check children folders
        children = folder_structure.get('Children', [])
        for child in children:
            if child.get('Name') == search_name:
                return child.get('Id')
            
        # Recursively check deeper in children
        for child in children:
            result = find_folder_id_by_name(child, search_name)
            if result:
                return result
    return None

def get_subfolders(folder_structure):
    """Get list of all subfolders"""
    folders = []
    
    if isinstance(folder_structure, dict):
        children = folder_structure.get('Children', [])
        for child in children:
            folders.append({
                'name': child.get('Name'),
                'id': child.get('Id')
            })
    
    return sorted(folders, key=lambda x: x['name'])

def find_launchpad_password_entry(folder_structure):
    """Find the LAUNCHPAD-OAUTH-BA-PASSWORD entry in the folder structure"""
    if isinstance(folder_structure, dict):
        # Check credentials in current folder
        credentials = folder_structure.get('Credentials', [])
        print(f"\nDebug - Found {len(credentials)} credentials in current folder: {folder_structure.get('Name', '')}")
        
        for cred in credentials:
            cred_name = cred.get('Name', '')
            print(f"Debug - Checking credential: {cred_name}")
            if 'LAUNCHPAD-OAUTH' in cred_name:
                print(f"Debug - Found matching credential!")
                return cred

        # Check in subfolders
        children = folder_structure.get('Children', [])
        print(f"Debug - Checking {len(children)} subfolders")
        for child in children:
            child_name = child.get('Name', '')
            print(f"Debug - Checking subfolder: {child_name}")
            result = find_launchpad_password_entry(child)
            if result:
                return result
    return None

def main():
    # Get authentication details from user input
    print("Pleasant Password Server Authentication")
    print("-" * 40)
    username = input("Username: ")
    password = getpass.getpass("Password: ")  # More secure way to input password
    
    # Initialize client
    client = PleasantPasswordClient(
        base_url="https://keeserver.gk.gk-software.com/api/v5/rest/",
        username=username,
        password=password
    )

    try:
        # First get the Projects folder structure
        projects_folder_id = "87300a24-9741-4d24-8a5c-a8b04e0b7049"
        folder_structure = client.get_folder(projects_folder_id)
        
        # Ask user for folder name to search
        search_name = input("\nEnter folder name to search (e.g., AZR-CSE): ")
        
        # Find folder ID
        folder_id = find_folder_id_by_name(folder_structure, search_name)
        
        if folder_id:
            print(f"\nFound folder '{search_name}'")
            print(f"Folder ID: {folder_id}")
            
            # Get folder contents
            folder_contents = client.get_folder(folder_id)
            subfolders = get_subfolders(folder_contents)
            
            if subfolders:
                print("\nAvailable subfolders:")
                print("-" * 20)
                for i, folder in enumerate(subfolders, 1):
                    print(f"{i}. {folder['name']}")
                
                # Ask user to select subfolder
                while True:
                    try:
                        choice = int(input("\nSelect subfolder number (or 0 to exit): "))
                        if choice == 0:
                            return
                        if 1 <= choice <= len(subfolders):
                            selected_folder = subfolders[choice - 1]
                            break
                        print("Invalid selection. Please try again.")
                    except ValueError:
                        print("Please enter a valid number.")
                
                # Get and save selected folder contents
                print(f"\nGetting contents for {selected_folder['name']}...")
                
                # Ask for recursion level
                recurse_level = int(input("\nEnter recursion level (0-5): ") or "1")
                
                # Get folder structure with specified recursion
                print("\nGetting full folder structure...")
                folder_structure = client.get_folder_by_id(selected_folder['id'], recurse_level=5)  # Get deeper structure
                
                # Find the Launchpad password entry automatically
                launchpad_entry = find_launchpad_password_entry(folder_structure)
                if launchpad_entry:
                    print("\nFound Launchpad OAuth entry:")
                    print("-" * 20)
                    print(f"Name: {launchpad_entry['Name']}")
                    entry_id = launchpad_entry['Id']
                    print(f"ID: {entry_id}")
                    
                    # Save folder structure first
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"folder_{selected_folder['name']}_{selected_folder['id']}_level{recurse_level}_{timestamp}.json"
                    
                    print(f"\nSaving folder structure to {filename}...")
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(folder_structure, f, indent=2)
                    
                    print(f"Folder structure saved successfully to {filename}")
                    
                    # Print folder structure
                    print("\nFolder Structure:")
                    print("-" * 20)
                    print(json.dumps(folder_structure, indent=2))
                    
                    # Now get entry details and password as the final operations
                    print(f"\nRetrieving entry {entry_id}...")
                    entry = client.get_entry_by_id(entry_id)
                    
                    print("\nEntry details:")
                    print("-" * 20)
                    print(json.dumps(entry, indent=2))

                    # Make the password call the very last operation
                    print("\nRetrieving password...")
                    try:
                        password = client._make_request('GET', f'credentials/{entry_id}/password')
                        
                        # Save password to separate file
                        password_filename = f"password_{entry_id}_{timestamp}.txt"
                        print(f"\nSaving password to {password_filename}...")
                        with open(password_filename, 'w', encoding='utf-8') as f:
                            f.write(str(password))
                        print(f"Password saved successfully to {password_filename}")
                        
                        print("\nPassword:")
                        print("-" * 20)
                        print(password)
                    except Exception as e:
                        print(f"\nError retrieving password: {e}")
                        print("(This might happen if a usage comment is required)")
                        print(f"Debug - Last attempted URL: {client.base_url}credentials/{entry_id}/password")
                else:
                    print(f"\nNo Launchpad OAuth password entry found in {selected_folder['name']}!")
            else:
                print("\nNo subfolders found in this location!")
        else:
            print(f"\nFolder '{search_name}' not found!")

    except Exception as e:
        print(f"\nError occurred: {e}")

if __name__ == "__main__":
    main() 