"""
Offline Package Helper Functions

This module contains helper functions extracted from the prepare_offline_package
method to improve modularity and reduce file size.
"""

import os
import time
import re
import customtkinter as ctk
import tkinter as tk
import sys


def download_file_thread(remote_path, local_path, file_name, component_type,
                         download_queue, concurrency_limiter, dsg_api_browser,
                         session, download_chunk_size):
    """
    Download a file in a separate thread with progress tracking

    Args:
        remote_path: Remote file path on the server
        local_path: Local path where file will be saved
        file_name: Display name of the file
        component_type: Type of component being downloaded
        download_queue: Queue for progress updates
        concurrency_limiter: Semaphore to limit concurrent downloads
        dsg_api_browser: DSG API browser instance
        session: Requests session instance
        download_chunk_size: Size of chunks to download
    """
    try:
        with concurrency_limiter:
            # Get the full URL for the file using REST API
            file_url = dsg_api_browser.get_file_url(remote_path)

            # Prepare headers with bearer token if available
            headers = dsg_api_browser._get_headers()

            print(f"Downloading from REST API: {file_url}")

            # Use requests session with streaming to track progress
            with session.get(
                file_url,
                headers=headers,
                stream=True,
                verify=False,
                timeout=(5, 180)
            ) as response:
                response.raise_for_status()

                # Get total file size if available
                total_size = int(response.headers.get('content-length', 0))

                # Initial progress update
                download_queue.put(("progress", (file_name, component_type, 0, total_size)))

                # Open local file for writing with larger buffer
                with open(local_path, 'wb', buffering=download_chunk_size) as f:
                    downloaded = 0
                    last_update_time = time.time()

                    # Download in chunks and update progress
                    for chunk in response.iter_content(chunk_size=download_chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Update progress every ~100ms to avoid flooding the queue
                            current_time = time.time()
                            if current_time - last_update_time > 0.1:
                                download_queue.put(("progress", (file_name, component_type, downloaded, total_size)))
                                last_update_time = current_time

                    # Final progress update
                    download_queue.put(("progress", (file_name, component_type, downloaded, total_size)))

            # Successfully downloaded
            download_queue.put(("complete", (file_name, component_type)))
    except Exception as e:
        print(f"Error downloading {file_name}: {e}")
        download_queue.put(("error", (file_name, component_type, str(e))))


def create_progress_dialog(parent, total_files):
    """
    Create a progress dialog for tracking file downloads

    Args:
        parent: Parent window
        total_files: Total number of files to download

    Returns:
        Tuple of (dialog, progress_bar, files_label, files_frame, file_progress_widgets, log_label)
    """
    progress_dialog = ctk.CTkToplevel(parent)
    progress_dialog.title("Downloading Files")
    progress_dialog.geometry("700x600")  # Increased size to accommodate multiple progress bars
    progress_dialog.transient(parent)

    # Force initial update
    progress_dialog.update_idletasks()

    # Linux-specific handling
    if sys.platform.startswith('linux'):
        progress_dialog.attributes("-topmost", True)
        progress_dialog.update()

    # Center the dialog on the parent window
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (700 // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (600 // 2)
    progress_dialog.geometry(f"+{x}+{y}")

    # Ensure focus and grab
    progress_dialog.focus_force()
    progress_dialog.grab_set()

    # Title
    ctk.CTkLabel(
        progress_dialog,
        text="Downloading Files",
        font=("Helvetica", 16, "bold")
    ).pack(pady=(20, 10), padx=20)

    # Progress frame
    progress_frame = ctk.CTkFrame(progress_dialog)
    progress_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # Overall progress bar
    ctk.CTkLabel(
        progress_frame,
        text="Overall Progress:",
        font=("Helvetica", 12)
    ).pack(pady=(10, 5), padx=10)

    progress_bar = ctk.CTkProgressBar(progress_frame, width=650)
    progress_bar.pack(pady=(0, 10), padx=10)
    progress_bar.set(0)

    # Files progress label
    files_label = ctk.CTkLabel(
        progress_frame,
        text=f"0/{total_files} files completed",
        font=("Helvetica", 12)
    )
    files_label.pack(pady=(0, 10), padx=10)

    # Create a scrollable frame for individual file progress bars
    ctk.CTkLabel(
        progress_frame,
        text="Individual File Progress:",
        font=("Helvetica", 12, "bold")
    ).pack(pady=(10, 5), padx=10, anchor="w")

    files_frame = ctk.CTkScrollableFrame(progress_frame, width=650, height=350)
    files_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # One more update to ensure everything is displayed
    progress_dialog.update_idletasks()

    # Dictionary to store progress bars and labels for each file
    file_progress_widgets = {}

    # We're removing the download log section
    # Return None for log_label since we're not using it anymore
    return progress_dialog, progress_bar, files_label, files_frame, file_progress_widgets, None


def prompt_for_file_selection(files, component_type, dialog_parent, parent_window,
                               title=None, description=None, file_type=None, config=None):
    """
    Prompt user to select files from a list when multiple files are found

    Args:
        files: List of file dictionaries from DSG API
        component_type: Type of component (for display)
        dialog_parent: Preferred parent window for dialog
        parent_window: Fallback parent window
        title: Custom dialog title (optional)
        description: Custom dialog description (optional)
        file_type: File type filter ("zip" or None)
        config: Configuration dictionary

    Returns:
        List of selected file dictionaries
    """
    # Use default config if not provided
    if config is None:
        config = {}

    # Use custom title and description if provided
    title = title or f"Select {component_type} Installer"
    description = description or f"Please select which installer(s) you want to download:"

    # Filter for appropriate file types
    if file_type == "zip":
        installable_files = [file for file in files if not file['is_directory'] and
                            file['name'].endswith('.zip')]
    else:
        # Get platform from config (default to Windows if not specified)
        platform = config.get("platform", "Windows")

        # Filter out Launcher files that don't match the current platform
        installable_files = []
        for file in files:
            if file['is_directory']:
                continue

            file_name = file['name']

            # Include JAR files
            if file_name.endswith('.jar'):
                installable_files.append(file)
            # Include EXE files only for Windows
            elif file_name.endswith('.exe'):
                if platform == 'Windows' or not file_name.startswith('Launcher'):
                    installable_files.append(file)
            # Include RUN files only for Linux
            elif file_name.endswith('.run'):
                if platform == 'Linux' or not file_name.startswith('Launcher'):
                    installable_files.append(file)

    # Separate Launcher file from other files (only for regular components)
    if file_type != "zip":
        # Get platform from config (default to Windows if not specified)
        platform = config.get("platform", "Windows")

        # Use appropriate launcher filename based on platform
        launcher_filename = 'Launcher.run' if platform == 'Linux' else 'Launcher.exe'

        launcher_files = [file for file in installable_files if file['name'] == launcher_filename]
        other_files = [file for file in installable_files if file['name'] != launcher_filename]
    else:
        launcher_files = []
        other_files = installable_files

    # If no files found, return empty list
    if len(installable_files) == 0:
        return []

    # If only Launcher.exe or no files, return all files directly
    if file_type != "zip" and len(other_files) == 0:
        return installable_files

    # If only one file (and it's not a dependency), return it directly
    if file_type != "zip" and len(other_files) == 1:
        return installable_files

    # Create a dialog to select files
    # Use the dialog_parent if provided, otherwise use parent_window, or create a new root
    parent = dialog_parent or parent_window
    if parent:
        dialog = ctk.CTkToplevel(parent)
        dialog.transient(parent)  # Make it transient to the parent
    else:
        # Create a temporary root window if no parent is available
        temp_root = tk.Tk()
        temp_root.withdraw()  # Hide the temporary root
        dialog = ctk.CTkToplevel(temp_root)

    dialog.title(title)
    dialog.geometry("600x500")  # Increased size for better visibility

    # Force initial update for Linux
    dialog.update_idletasks()

    # Linux-specific handling
    if sys.platform.startswith('linux'):
        dialog.attributes("-topmost", True)
        dialog.update()

    # Focus and grab management
    dialog.focus_force()
    dialog.grab_set()

    # Center the dialog on the parent window if available
    if parent:
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (600 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (500 // 2)
        dialog.geometry(f"+{x}+{y}")

    # Title and description
    ctk.CTkLabel(
        dialog,
        text=title,
        font=("Helvetica", 16, "bold")
    ).pack(pady=(20, 5), padx=20)

    ctk.CTkLabel(
        dialog,
        text=description,
        font=("Helvetica", 12)
    ).pack(pady=(0, 20), padx=20)

    # If Launcher.exe exists, show a message that it will be downloaded automatically
    if launcher_files:
        # Get platform from config (default to Windows if not specified)
        platform = config.get("platform", "Windows")

        # Use appropriate launcher filename based on platform
        launcher_filename = 'Launcher.run' if platform == 'Linux' else 'Launcher.exe'

        launcher_label = ctk.CTkLabel(
            dialog,
            text=f"Note: {launcher_filename} will be downloaded automatically",
            font=("Helvetica", 12, "italic"),
            text_color="gray"
        )
        launcher_label.pack(pady=(0, 10), padx=20)

    # Create a scrollable frame for the checkboxes
    scroll_frame = ctk.CTkScrollableFrame(dialog, width=450, height=200)
    scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # Update to ensure scroll_frame is properly rendered
    dialog.update_idletasks()

    # Find the latest version (assuming version numbers are in the filenames)
    # This is a simple heuristic - we'll try to find the file with the highest version number
    latest_file = None

    # First, try to find files with version numbers in format x.y.z
    version_pattern = re.compile(r'(\d+\.\d+\.\d+)')
    versioned_files = []

    for file in other_files:
        match = version_pattern.search(file['name'])
        if match:
            version = match.group(1)
            versioned_files.append((file, version))

    if versioned_files:
        # Sort by version number (as string, which works for simple version formats)
        versioned_files.sort(key=lambda x: [int(n) for n in x[1].split('.')])
        latest_file = versioned_files[-1][0]  # Get the file with the highest version

    # If no versioned files found, try to use date in filename or just pick the last file
    if not latest_file:
        # Try to find date patterns (YYYYMMDD or similar)
        date_pattern = re.compile(r'(\d{8}|\d{6})')
        dated_files = []

        for file in other_files:
            match = date_pattern.search(file['name'])
            if match:
                date = match.group(1)
                dated_files.append((file, date))

        if dated_files:
            # Sort by date (as string)
            dated_files.sort(key=lambda x: x[1])
            latest_file = dated_files[-1][0]  # Get the file with the latest date
        else:
            # If all else fails, just pick the last file in the list
            # Sort alphabetically first to ensure consistent behavior
            sorted_files = sorted(other_files, key=lambda x: x['name'])
            latest_file = sorted_files[-1] if sorted_files else None

    # Create variables to track selections
    selected_vars = {}

    # For Java files, identify the latest version for each platform
    latest_windows_java = None
    latest_linux_java = None

    if component_type and 'Java' in component_type:
        # Get platform from config
        platform = config.get("platform", "Windows")
        print(f"Current platform for Java selection: {platform}")

        # Find all Java files for each platform
        windows_java_files = []
        linux_java_files = []

        for file in other_files:
            file_name = file['name'].lower()
            if "java" in component_type.lower():
                # Collect Windows Java files - check both zuludk and zulujre patterns
                if ("windows" in file_name and
                    ("zulujdk" in file_name or "zuludk" in file_name or "zulujre" in file_name)):
                    print(f"Found Windows Java file: {file['name']}")
                    windows_java_files.append(file)
                # Collect Linux Java files - check both zuludk and zulujre patterns
                elif ("linux" in file_name and
                      ("zulujdk" in file_name or "zuludk" in file_name or "zulujre" in file_name)):
                    print(f"Found Linux Java file: {file['name']}")
                    linux_java_files.append(file)

        # Parse version numbers for better sorting
        def extract_version(filename):
            # Extract version like 11.0.18 or 1.8.0_362
            version_match = re.search(r'(\d+\.\d+\.\d+(?:_\d+)?)', filename)
            if version_match:
                version_str = version_match.group(1)
                # Convert to tuple for comparison
                if '_' in version_str:
                    # Handle Java 8 style (1.8.0_362)
                    main_version, update = version_str.split('_')
                    parts = main_version.split('.')
                    return (int(parts[0]), int(parts[1]), int(parts[2]), int(update))
                else:
                    # Handle Java 11+ style (11.0.18)
                    parts = version_str.split('.')
                    return tuple(int(p) for p in parts)
            return (0, 0, 0)  # Default if no version found

        # Sort Windows Java files by version
        if windows_java_files:
            # Sort by parsed version numbers
            windows_java_files.sort(key=lambda x: extract_version(x['name']))
            latest_windows_java = windows_java_files[-1]
            print(f"Latest Windows Java: {latest_windows_java['name']}")

        # Sort Linux Java files by version
        if linux_java_files:
            # Sort by parsed version numbers
            linux_java_files.sort(key=lambda x: extract_version(x['name']))
            latest_linux_java = linux_java_files[-1]
            print(f"Latest Linux Java: {latest_linux_java['name']}")

    for file in other_files:
        # Default to not selected
        default_selected = False

        # For Java files, select based on platform
        if component_type and 'Java' in component_type:
            platform = config.get("platform", "Windows")
            file_name = file['name'].lower()

            # For Windows platform, select the latest Windows Java
            if platform == "Windows":
                if latest_windows_java and file['name'] == latest_windows_java['name']:
                    print(f"Pre-selecting Windows Java: {file['name']}")
                    default_selected = True
            # For Linux platform, select the latest Linux Java
            elif platform == "Linux":
                if latest_linux_java and file['name'] == latest_linux_java['name']:
                    print(f"Pre-selecting Linux Java: {file['name']}")
                    default_selected = True
        # For non-Java files, use the latest file logic
        elif file == latest_file:
            default_selected = True

        var = ctk.BooleanVar(value=default_selected)
        selected_vars[file['name']] = var
        checkbox = ctk.CTkCheckBox(
            scroll_frame,
            text=file['name'],
            variable=var,
            checkbox_width=20,
            checkbox_height=20
        )
        checkbox.pack(anchor="w", pady=5, padx=10)

    # Add select all / deselect all buttons
    buttons_frame = ctk.CTkFrame(dialog)
    buttons_frame.pack(fill="x", pady=(0, 10), padx=20)

    def select_all():
        for var in selected_vars.values():
            var.set(True)

    def deselect_all():
        for var in selected_vars.values():
            var.set(False)

    ctk.CTkButton(
        buttons_frame,
        text="Select All",
        command=select_all,
        width=100,
        height=25,
        fg_color="#555555",
        hover_color="#333333"
    ).pack(side="left", padx=5)

    ctk.CTkButton(
        buttons_frame,
        text="Deselect All",
        command=deselect_all,
        width=100,
        height=25,
        fg_color="#555555",
        hover_color="#333333"
    ).pack(side="left", padx=5)

    # Result variable
    result = []

    # OK button handler
    def on_ok():
        nonlocal result
        # Always include Launcher.exe files
        result = launcher_files.copy()
        # Add selected non-Launcher files
        result.extend([file for file in other_files if selected_vars[file['name']].get()])
        dialog.destroy()
        if not parent:
            temp_root.destroy()  # Clean up the temporary root if we created one

    # Cancel button handler
    def on_cancel():
        nonlocal result
        # Always include Launcher.exe files even on cancel
        result = launcher_files.copy()
        dialog.destroy()
        if not parent:
            temp_root.destroy()  # Clean up the temporary root if we created one

    # Buttons
    button_frame = ctk.CTkFrame(dialog)
    button_frame.pack(fill="x", pady=20, padx=20)

    ctk.CTkButton(
        button_frame,
        text="Cancel",
        command=on_cancel,
        width=100,
        fg_color="#555555",
        hover_color="#333333"
    ).pack(side="left", padx=10)

    ctk.CTkButton(
        button_frame,
        text="Download Selected",
        command=on_ok,
        width=150
    ).pack(side="right", padx=10)

    # Wait for the dialog to close
    if parent:
        parent.wait_window(dialog)
    else:
        # If we don't have a parent window, use a different approach
        dialog.wait_window()

    return result


def process_platform_dependency(dep_name, dep_key, api_path, file_extension,
                                platform_dependencies, dsg_api_browser,
                                ask_download_again_callback, dialog_parent,
                                output_dir, files_to_download, download_errors,
                                prompt_for_file_selection_callback, config,
                                file_filter=None):
    """
    Process a platform dependency download (Java, Tomcat, Jaybird)

    Args:
        dep_name: Display name (e.g., 'Java', 'Tomcat')
        dep_key: Config key (e.g., 'JAVA', 'TOMCAT')
        api_path: API path (e.g., '/SoftwarePackage/Java')
        file_extension: File extension to check (e.g., 'zip', 'jar')
        platform_dependencies: Dictionary of platform dependencies from config
        dsg_api_browser: DSG API browser instance
        ask_download_again_callback: Callback to ask user if they want to re-download
        dialog_parent: Parent window for dialogs
        output_dir: Output directory path
        files_to_download: List to append download tasks to
        download_errors: List to append errors to
        prompt_for_file_selection_callback: Callback to prompt for file selection
        config: Configuration dictionary
        file_filter: Optional filter function for files
    """
    if not platform_dependencies.get(dep_key, False):
        return

    print(f"\nProcessing {dep_name} platform dependency...")
    dep_dir = os.path.join(output_dir, dep_name)
    os.makedirs(dep_dir, exist_ok=True)
    print(f"Checking {dep_name} directory: {api_path}")

    try:
        # Check if files already exist
        existing_files = [f for f in os.listdir(dep_dir) if f.endswith(f'.{file_extension}')]
        if existing_files:
            download = ask_download_again_callback(dep_name, existing_files, dialog_parent)
            if not download:
                print(f"Skipping {dep_name} download as files already exist")
                return

        # List files from REST API
        files = dsg_api_browser.list_directories(api_path)
        print(f"Found {dep_name} items: {files}")

        # Apply filter if provided
        if file_filter:
            files = file_filter(files)
            if not files:
                print(f"No matching {dep_name} files found after filtering")
                download_errors.append(f"No matching {dep_name} files found")
                return

        # Check if we have direct files or version directories
        direct_files = [f for f in files if not f.get('is_directory', False) and
                       f.get('name', '').endswith(f'.{file_extension}')]
        version_dirs = [f for f in files if f.get('is_directory', False)]

        print(f"Direct {file_extension} files: {len(direct_files)}, Version directories: {len(version_dirs)}")

        # If we have version directories but no direct files, let user select a version first
        if not direct_files and version_dirs:
            print(f"No direct {file_extension} files found, prompting user to select version directory...")

            # Create a simple dialog to select version directory
            selected_version = _prompt_for_version_selection(
                version_dirs, dep_name, dialog_parent,
                f"Select {dep_name} Version",
                f"Please select which {dep_name} version to download:"
            )

            if not selected_version:
                print(f"No {dep_name} version selected")
                return

            # Navigate into the selected version directory
            version_path = f"{api_path}/{selected_version}"
            print(f"Listing contents of version directory: {version_path}")
            files = dsg_api_browser.list_directories(version_path)
            print(f"Found files in version directory: {files}")

            # Update api_path for the download
            api_path = version_path

        # Prompt user to select files
        selected_files = prompt_for_file_selection_callback(
            files,
            dep_name,
            dialog_parent,
            dialog_parent,  # Use dialog_parent as fallback too
            title=f"Select {dep_name} Files",
            description=f"Please select which {dep_name} {'driver' if dep_key == 'JAYBIRD' else 'files'} to download:",
            file_type=file_extension,
            config=config
        )

        # Add selected files to download list
        for file in selected_files:
            file_name = file['name']
            remote_path = f"{api_path}/{file_name}"
            local_path = os.path.join(dep_dir, file_name)
            files_to_download.append((remote_path, local_path, file_name, dep_name))

    except Exception as e:
        print(f"Error accessing {dep_name} directory: {e}")
        download_errors.append(f"Failed to access {dep_name} directory: {str(e)}")


def _prompt_for_version_selection(version_dirs, dep_name, dialog_parent, title, description):
    """
    Prompt user to select a version directory

    Returns:
        Selected version name (string) or None if cancelled
    """
    import tkinter as tk

    # Sort versions (try natural version sorting)
    sorted_versions = sorted(version_dirs, key=lambda x: x.get('name', ''), reverse=True)

    selected_version = [None]  # Use list to allow modification in nested function

    # Create dialog
    parent = dialog_parent
    if parent:
        dialog = ctk.CTkToplevel(parent)
        dialog.transient(parent)
    else:
        temp_root = tk.Tk()
        temp_root.withdraw()
        dialog = ctk.CTkToplevel(temp_root)

    dialog.title(title)
    dialog.geometry("400x400")
    dialog.grab_set()

    # Center dialog
    if parent:
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 200
        dialog.geometry(f"+{x}+{y}")

    # Title
    ctk.CTkLabel(dialog, text=title, font=("Helvetica", 16, "bold")).pack(pady=(20, 5))
    ctk.CTkLabel(dialog, text=description, font=("Helvetica", 12)).pack(pady=(0, 10))

    # Version list
    list_frame = ctk.CTkScrollableFrame(dialog, width=350, height=250)
    list_frame.pack(fill="both", expand=True, padx=20, pady=10)

    version_var = tk.StringVar()

    for ver in sorted_versions:
        ver_name = ver.get('name', '')
        rb = ctk.CTkRadioButton(list_frame, text=ver_name, variable=version_var, value=ver_name)
        rb.pack(anchor="w", pady=2)

    # Select first version by default
    if sorted_versions:
        version_var.set(sorted_versions[0].get('name', ''))

    def on_ok():
        selected_version[0] = version_var.get()
        dialog.destroy()

    def on_cancel():
        dialog.destroy()

    # Buttons
    btn_frame = ctk.CTkFrame(dialog)
    btn_frame.pack(fill="x", padx=20, pady=10)

    ctk.CTkButton(btn_frame, text="OK", command=on_ok, width=100).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="Cancel", command=on_cancel, width=100).pack(side="right", padx=5)

    dialog.wait_window()

    return selected_version[0]


def process_component(component_name, component_key, config_key, default_system_type,
                      selected_components, output_dir, config, get_component_version_callback,
                      dsg_api_browser, prompt_for_file_selection_callback,
                      files_to_download, dialog_parent, parent_window, display_name=None):
    """
    Process an application component download

    Args:
        component_name: Component identifier (e.g., 'POS', 'WDM')
        component_key: Key in selected_components list
        config_key: Config key prefix (e.g., 'pos', 'wdm')
        default_system_type: Default system type if not in config
        selected_components: List of selected components
        output_dir: Output directory path
        config: Configuration dictionary
        get_component_version_callback: Callback to get component version
        dsg_api_browser: DSG API browser instance
        prompt_for_file_selection_callback: Callback to prompt for file selection
        files_to_download: List to append download tasks to
        dialog_parent: Preferred parent window for dialogs
        parent_window: Fallback parent window
        display_name: Optional display name (defaults to component_name)
    """
    if component_key not in selected_components:
        return

    display_name = display_name or component_name
    component_dir = os.path.join(output_dir, f"offline_package_{component_name}")
    print(f"\nProcessing {display_name} component...")
    print(f"Output directory: {component_dir}")
    os.makedirs(component_dir, exist_ok=True)

    # Determine system type and version
    system_type = config.get(f"{config_key}_system_type", default_system_type)
    version_to_use = get_component_version_callback(system_type, config)

    print(f"Using system type: {system_type}")
    print(f"Using version: {version_to_use}")

    # Navigate to version directory
    version_path = f"/SoftwarePackage/{system_type}/{version_to_use}"
    print(f"Checking version directory: {version_path}")

    try:
        files = dsg_api_browser.list_directories(version_path)
        print(f"Found files: {files}")

        # Prompt user to select files
        selected_files = prompt_for_file_selection_callback(
            files, display_name, dialog_parent, parent_window,
            title=f"Select {display_name} Installer",
            description=f"Please select which {display_name} installer(s) you want to download:",
            file_type=None,
            config=config
        )

        # Add selected files to download list
        for file in selected_files:
            file_name = file['name']
            remote_path = f"{version_path}/{file_name}"
            local_path = os.path.join(component_dir, file_name)

            # Make launcher names more specific
            file_display_name = file_name
            if file_name.startswith("Launcher."):
                file_display_name = f"{display_name} {file_name}"

            files_to_download.append((remote_path, local_path, file_display_name, display_name))

    except Exception as e:
        print(f"Error accessing {display_name} version directory: {e}")
        raise


def process_onex_ui_package(selected_components, output_dir, config, get_component_version_callback,
                            dsg_api_browser, files_to_download):
    """
    Process the OneX UI package download (platform-specific zip).

    Downloads the onex-ui-{version}-{platform}.zip file from the same DSG path
    as the OneX POS installer, placing it in the same offline_package_ONEX-POS directory.

    Args:
        selected_components: List of selected components
        output_dir: Output directory path
        config: Configuration dictionary
        get_component_version_callback: Callback to get component version
        dsg_api_browser: DSG API browser instance
        files_to_download: List to append download tasks to
    """
    if "ONEX-POS-UI" not in selected_components:
        return

    print("\nProcessing OneX UI package...")

    # Reuse the same system type and version as OneX POS
    system_type = config.get("onex_pos_system_type", "CSE-OPOS-ONEX-CLOUD")
    version_to_use = get_component_version_callback(system_type, config)
    component_dir = os.path.join(output_dir, "offline_package_ONEX-POS")
    os.makedirs(component_dir, exist_ok=True)

    # Determine platform suffix
    platform_type = config.get("platform", "Windows")
    if platform_type.lower() == "linux":
        platform_suffix = "-linux.zip"
    else:
        platform_suffix = "-windows.zip"

    version_path = f"/SoftwarePackage/{system_type}/{version_to_use}"
    print(f"Looking for OneX UI package in: {version_path}")

    try:
        files = dsg_api_browser.list_directories(version_path)

        # Filter for the platform-specific UI zip
        ui_files = [f for f in files if f.get('name', '').startswith('onex-ui-')
                     and f.get('name', '').endswith(platform_suffix)]

        if not ui_files:
            print(f"Warning: No OneX UI package found matching *{platform_suffix} in {version_path}")
            return

        # Auto-select the single matching file
        ui_file = ui_files[0]
        file_name = ui_file['name']
        remote_path = f"{version_path}/{file_name}"
        local_path = os.path.join(component_dir, file_name)

        print(f"Found OneX UI package: {file_name}")
        files_to_download.append((remote_path, local_path, file_name, "OneX POS Client"))

    except Exception as e:
        print(f"Error accessing OneX UI package: {e}")
