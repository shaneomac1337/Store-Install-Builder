"""
About dialog for Store-Install-Builder
"""
import os
import sys
import customtkinter as ctk

try:
    from gk_install_builder.ui.helpers import bind_mousewheel_to_frame
except ImportError:
    from ui.helpers import bind_mousewheel_to_frame


class AboutDialog:
    """Display application information and credits"""

    def __init__(self, parent_window):
        """
        Initialize About dialog.

        Args:
            parent_window: Parent window for the dialog
        """
        self.parent = parent_window
        self.window = None

    def show(self):
        """Display the about dialog"""
        # Create a new toplevel window
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("About")
        # Make the window taller to fit all content including copyright
        self.window.geometry("400x750")

        # Add these lines to fix Linux visibility issue
        self.window.update_idletasks()
        self.window.update()

        self.window.transient(self.parent)

        # Try-except block to handle potential grab_set issues on Linux
        try:
            self.window.grab_set()
        except Exception as e:
            print(f"Warning: Could not set grab on About window: {str(e)}")

        self.window.resizable(False, False)

        # Ensure the window appears on top
        self.window.focus_force()

        # Main content frame
        content_frame = ctk.CTkScrollableFrame(self.window)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Apply mousewheel binding for Linux scrolling
        bind_mousewheel_to_frame(content_frame)

        # Force another update to ensure contents are displayed
        self.window.after(100, self.window.update_idletasks)
        self.window.after(100, self.window.update)

        # Logo frame with more padding at the top
        logo_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        logo_frame.pack(pady=(15, 5))  # Reduced top padding to make more room below

        # Check if logo file exists and use it
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "gk_logo.png")

        if os.path.exists(logo_path):
            try:
                # Load the image using PIL/Pillow
                from PIL import Image
                original_image = Image.open(logo_path)

                # Get original dimensions to calculate proper aspect ratio
                orig_width, orig_height = original_image.size

                # Set a fixed width and calculate height based on aspect ratio
                display_width = 140
                display_height = int((display_width / orig_width) * orig_height)

                # Create the image with proper aspect ratio
                logo_image = ctk.CTkImage(
                    light_image=original_image,
                    dark_image=original_image,
                    size=(display_width, display_height)  # Size that preserves aspect ratio
                )

                logo_label = ctk.CTkLabel(
                    logo_frame,
                    image=logo_image,
                    text=""
                )
                logo_label.pack()

            except Exception as e:
                print(f"Error loading logo: {str(e)}")
                self._create_fallback_logo(logo_frame)
        else:
            self._create_fallback_logo(logo_frame)

        # App title
        title_label = ctk.CTkLabel(
            content_frame,
            text="GK Install Builder",
            font=("Helvetica", 18, "bold")
        )
        title_label.pack(pady=(5, 0))

        # Version
        version_label = ctk.CTkLabel(
            content_frame,
            text="Version 5.27",
            font=("Helvetica", 12),
            text_color=("gray50", "gray70")
        )
        version_label.pack(pady=(0, 5))

        # Copyright information - Moving these up in the layout, before technical info
        copyright_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        copyright_frame.pack(fill="x", padx=5, pady=0)

        copyright_label = ctk.CTkLabel(
            copyright_frame,
            text="© Created in 2025 by Martin Pěnkava",
            font=("Helvetica", 12),
            text_color=("gray50", "gray70")
        )
        copyright_label.pack(pady=5)

        # Contact info - Moving up with copyright
        contact_label = ctk.CTkLabel(
            copyright_frame,
            text="Contact: mpenkava@gk-software.com",
            font=("Helvetica", 12),
            text_color=("#3a7ebf", "#2b5f8f"),  # Blue text
            cursor="hand2"  # Hand cursor
        )
        contact_label.pack(pady=2)

        # Description
        description_label = ctk.CTkLabel(
            content_frame,
            text="GK Automation tool for creating installation packages for retail systems.",
            font=("Helvetica", 12),
            wraplength=350,
            justify="center"
        )
        description_label.pack(pady=(5, 15))

        # Divider
        divider = ctk.CTkFrame(content_frame, height=1, fg_color=("gray70", "gray30"))
        divider.pack(fill="x", padx=20, pady=5)

        # Technical info frame
        info_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        info_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Technical info header
        tech_title = ctk.CTkLabel(
            info_frame,
            text="Technical Information",
            font=("Helvetica", 14, "bold"),
            justify="left"
        )
        tech_title.pack(anchor="w", padx=10, pady=(5, 10))

        # Get system information
        import platform as pf

        # Simple function to add info rows
        def add_info_row(label, value):
            frame = ctk.CTkFrame(info_frame, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=5)

            label_widget = ctk.CTkLabel(
                frame,
                text=f"{label}:",
                font=("Helvetica", 12, "bold"),
                width=120,
                anchor="w"
            )
            label_widget.pack(side="left")

            value_widget = ctk.CTkLabel(
                frame,
                text=value,
                font=("Helvetica", 12),
                anchor="w",
                wraplength=220  # Fixed reasonable wraplength
            )
            value_widget.pack(side="left")

        # Add technical information with increased spacing
        add_info_row("Platform", pf.system())
        add_info_row("Python", sys.version.split()[0])
        add_info_row("CustomTkinter", ctk.__version__)

        # Components with longer text needs more space
        components_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        components_frame.pack(fill="x", padx=10, pady=5)

        components_label = ctk.CTkLabel(
            components_frame,
            text="Supports:",
            font=("Helvetica", 12, "bold"),
            width=120,
            anchor="w"
        )
        components_label.pack(side="left", anchor="n")

        components_value = ctk.CTkLabel(
            components_frame,
            text="POS, WDM, Flow Service,\nLPA, StoreHub",
            font=("Helvetica", 12),
            justify="left",
            anchor="w"
        )
        components_value.pack(side="left", anchor="n")

        # Close button
        close_button = ctk.CTkButton(
            content_frame,
            text="Close",
            command=self.window.destroy,
            width=100
        )
        close_button.pack(pady=10)

    def _create_fallback_logo(self, parent_frame):
        """Create a fallback text-based logo button"""
        logo_button = ctk.CTkButton(
            parent_frame,
            text="GK",  # Placeholder for logo
            font=("Helvetica", 28, "bold"),
            width=60,
            height=60,
            corner_radius=30,  # Circular button
            fg_color=("#3a7ebf", "#2b5f8f"),  # Blue background with dark variant
            hover_color=("#2b5f8f", "#1a4060"),  # Darker blue on hover
            text_color="white",  # White text
            command=None  # No action
        )
        logo_button.pack()


def show_about_dialog(parent_window):
    """
    Show the about dialog (convenience function).

    Args:
        parent_window: Parent window for the dialog
    """
    dialog = AboutDialog(parent_window)
    dialog.show()
