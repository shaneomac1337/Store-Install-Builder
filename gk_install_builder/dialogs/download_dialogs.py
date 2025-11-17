"""
Download-related dialog functions

This module contains dialog functions for download operations,
extracted from generator.py to improve modularity.
"""

import customtkinter as ctk
import tkinter as tk
import sys


def ask_download_again(component_type, existing_files, parent_window=None):
    """
    Ask the user if they want to download files again when they already exist.

    Args:
        component_type (str): The type of component (e.g., "POS Java")
        existing_files (list): List of existing files
        parent_window: Parent window for the dialog

    Returns:
        bool: True if the user wants to download again, False otherwise
    """
    # Use the parent if provided
    parent = parent_window

    # Format the list of existing files
    files_str = "\n".join(existing_files)

    if parent:
        # Create a dialog
        result = [False]  # Use a list to store the result (to be modified by inner functions)

        dialog = ctk.CTkToplevel(parent)
        dialog.title(f"Existing {component_type} Files Found")
        dialog.geometry("600x450")
        dialog.transient(parent)

        # Force update to ensure dialog is properly created
        dialog.update_idletasks()

        # Linux-specific handling
        if sys.platform.startswith('linux'):
            dialog.attributes("-topmost", True)
            dialog.update()

        dialog.grab_set()
        dialog.focus_force()

        # Title
        ctk.CTkLabel(
            dialog,
            text=f"Existing {component_type} Files Found",
            font=("Helvetica", 16, "bold")
        ).pack(pady=(20, 10), padx=20)

        # Message
        ctk.CTkLabel(
            dialog,
            text=f"The following {component_type} files already exist:",
            font=("Helvetica", 12)
        ).pack(pady=(0, 10), padx=20)

        # Create a scrollable frame for the files list
        files_frame = ctk.CTkScrollableFrame(dialog, width=550, height=200)
        files_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Add files to the scrollable frame
        for file in existing_files:
            ctk.CTkLabel(
                files_frame,
                text=file,
                font=("Helvetica", 11),
                anchor="w"
            ).pack(fill="x", padx=5, pady=2, anchor="w")

        # Question
        ctk.CTkLabel(
            dialog,
            text="Do you want to download these files again?",
            font=("Helvetica", 12)
        ).pack(pady=(10, 20), padx=20)

        # Buttons
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(fill="x", pady=(0, 20), padx=20)

        def on_yes():
            result[0] = True
            dialog.destroy()

        def on_no():
            result[0] = False
            dialog.destroy()

        ctk.CTkButton(
            button_frame,
            text="No, Skip Download",
            command=on_no,
            width=180,
            fg_color="#555555",
            hover_color="#333333"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            button_frame,
            text="Yes, Download Again",
            command=on_yes,
            width=180
        ).pack(side="right", padx=10)

        # One more update to ensure everything is displayed
        dialog.update_idletasks()

        # Wait for the dialog to close
        parent.wait_window(dialog)

        return result[0]
    else:
        # If no parent window, use console input
        print(f"\nExisting {component_type} files found:")
        for file in existing_files:
            print(f"  - {file}")

        while True:
            response = input(f"Do you want to download {component_type} files again? (y/n): ").lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'.")


def ask_download_dependencies_only(component_type, parent_window=None, error_message=None):
    """
    Ask user if they want to download dependencies even if component files are not found

    Args:
        component_type (str): The type of component (e.g., "POS")
        parent_window: Parent window for the dialog
        error_message: Optional error message to display

    Returns:
        bool: True if user wants to download dependencies, False otherwise
    """
    # Create message based on whether there was an error or just no files found
    if error_message:
        message = f"{component_type} files could not be accessed: {error_message}\n\nWould you like to download Java and Tomcat dependencies anyway?"
    else:
        message = f"No {component_type} files were found.\n\nWould you like to download Java and Tomcat dependencies anyway?"

    # Use the parent if provided
    if parent_window:
        dialog = ctk.CTkToplevel(parent_window)
        dialog.transient(parent_window)  # Make it transient to the parent
    else:
        # Create a temporary root window if no parent is available
        temp_root = tk.Tk()
        temp_root.withdraw()  # Hide the temporary root
        dialog = ctk.CTkToplevel(temp_root)

    dialog.title(f"{component_type} Files Not Found")
    dialog.geometry("500x200")

    # Force initial update
    dialog.update_idletasks()

    # Linux-specific handling
    if sys.platform.startswith('linux'):
        dialog.attributes("-topmost", True)
        dialog.update()

    # Center the dialog on the parent window if available
    if parent_window:
        x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - (500 // 2)
        y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - (200 // 2)
        dialog.geometry(f"+{x}+{y}")

    # Ensure focus and grab
    dialog.focus_force()
    dialog.grab_set()

    # Result variable
    result = False

    # Title and message
    ctk.CTkLabel(
        dialog,
        text=f"{component_type} Files Not Found",
        font=("Helvetica", 16, "bold")
    ).pack(pady=(20, 5), padx=20)

    ctk.CTkLabel(
        dialog,
        text=message,
        font=("Helvetica", 12),
        wraplength=450
    ).pack(pady=(0, 20), padx=20)

    # Yes button handler
    def on_yes():
        nonlocal result
        result = True
        dialog.destroy()
        if not parent_window:
            temp_root.destroy()  # Clean up the temporary root if we created one

    # No button handler
    def on_no():
        nonlocal result
        result = False
        dialog.destroy()
        if not parent_window:
            temp_root.destroy()  # Clean up the temporary root if we created one

    # Buttons
    button_frame = ctk.CTkFrame(dialog)
    button_frame.pack(fill="x", pady=20, padx=20)

    ctk.CTkButton(
        button_frame,
        text="No",
        command=on_no,
        width=100,
        fg_color="#555555",
        hover_color="#333333"
    ).pack(side="left", padx=10)

    ctk.CTkButton(
        button_frame,
        text="Yes, Download Dependencies",
        command=on_yes,
        width=200
    ).pack(side="right", padx=10)

    # One more update to ensure everything is displayed
    dialog.update_idletasks()

    # Wait for the dialog to close
    if parent_window:
        parent_window.wait_window(dialog)
    else:
        # If we don't have a parent window, use a different approach
        dialog.wait_window()

    return result
