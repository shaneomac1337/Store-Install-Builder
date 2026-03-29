"""
Generation Summary Dialog

Modal dialog shown after successful file generation.
Displays config snapshot, file counts by category, and informational notes.
"""
import os
import sys
import subprocess
import customtkinter as ctk

try:
    from gk_install_builder.ui.helpers import bind_mousewheel_to_frame
except ImportError:
    from ui.helpers import bind_mousewheel_to_frame


class GenerationSummaryDialog:
    """Modal summary dialog shown after generation completes."""

    # Display names for file categories
    CATEGORY_LABELS = {
        "scripts": "Scripts",
        "launchers": "Launchers",
        "configs": "Configs",
        "tokens": "Tokens",
        "overrides": "Overrides",
        "other": "Other",
    }

    # Display order for categories
    CATEGORY_ORDER = ["scripts", "launchers", "configs", "tokens", "overrides", "other"]

    def __init__(self, parent, tracker):
        """
        Initialize and display the generation summary dialog.

        Args:
            parent: Parent CTk window
            tracker: GenerationTracker instance with collected results
        """
        self.parent = parent
        self.tracker = tracker
        self.window = None
        self._show()

    def _show(self):
        """Build and display the modal dialog."""
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("Generation Summary")
        self.window.geometry("500x500")
        self.window.resizable(False, False)

        # Modal behavior (same pattern as about.py and other dialogs)
        self.window.update_idletasks()
        self.window.update()
        self.window.transient(self.parent)
        try:
            self.window.grab_set()
        except Exception:
            pass

        # Center on parent
        self.window.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        win_w = 500
        win_h = 500
        x = parent_x + (parent_w - win_w) // 2
        y = parent_y + (parent_h - win_h) // 2
        self.window.geometry(f"{win_w}x{win_h}+{x}+{y}")

        self.window.focus_force()

        # Scrollable content
        content = ctk.CTkScrollableFrame(self.window)
        content.pack(fill="both", expand=True, padx=15, pady=(15, 5))

        # Apply mousewheel binding for Linux scrolling
        bind_mousewheel_to_frame(content)

        # Header
        ctk.CTkLabel(
            content, text="Generation Complete",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=(0, 10))

        # Configuration section
        self._build_config_section(content)

        # Files section
        self._build_files_section(content)

        # Notes section (only if there are notes)
        notes = self.tracker.get_notes()
        if notes:
            self._build_notes_section(content, notes)

        # Button frame (outside scrollable area)
        button_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(5, 15))

        output_dir = self.tracker.get_config_snapshot().get("output_dir", "")

        ctk.CTkButton(
            button_frame, text="Open Folder",
            command=lambda: self._open_folder(output_dir),
            width=120
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            button_frame, text="Close",
            command=self.window.destroy,
            width=80, fg_color="gray40", hover_color="gray30"
        ).pack(side="left")

    def _build_config_section(self, parent):
        """Build the Configuration section."""
        ctk.CTkLabel(
            parent, text="Configuration",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(5, 5))

        config_frame = ctk.CTkFrame(parent)
        config_frame.pack(fill="x", pady=(0, 10))

        snap = self.tracker.get_config_snapshot()
        api_display = "New (5.27+)" if snap.get("api_version") == "new" else "Legacy (5.25)"

        rows = [
            ("Platform:", snap.get("platform", "N/A")),
            ("Base URL:", snap.get("base_url", "N/A")),
            ("Tenant ID:", snap.get("tenant_id", "N/A")),
            ("API Version:", api_display),
            ("Output:", snap.get("output_dir", "N/A")),
        ]

        for label_text, value_text in rows:
            row = ctk.CTkFrame(config_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=label_text, width=100, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left")
            ctk.CTkLabel(row, text=value_text, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left", fill="x", expand=True)

    def _build_files_section(self, parent):
        """Build the Generated Files section."""
        total = self.tracker.get_total_file_count()
        ctk.CTkLabel(
            parent, text=f"Generated Files ({total} files)",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(5, 5))

        files_frame = ctk.CTkFrame(parent)
        files_frame.pack(fill="x", pady=(0, 10))

        counts = self.tracker.get_file_counts()
        for cat in self.CATEGORY_ORDER:
            count = counts.get(cat, 0)
            if count == 0:
                continue
            row = ctk.CTkFrame(files_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            label = self.CATEGORY_LABELS.get(cat, cat.title())
            ctk.CTkLabel(row, text=f"{label}:", width=100, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left")
            ctk.CTkLabel(row, text=str(count), anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left")

    def _build_notes_section(self, parent, notes):
        """Build the Notes section."""
        ctk.CTkLabel(
            parent, text="Notes",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(5, 5))

        notes_frame = ctk.CTkFrame(parent)
        notes_frame.pack(fill="x", pady=(0, 10))

        for note in notes:
            row = ctk.CTkFrame(notes_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=f"- {note}", anchor="w", wraplength=420,
                         font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _open_folder(self, output_dir):
        """Open the output directory in the system file manager."""
        if not output_dir or not os.path.isdir(output_dir):
            return
        try:
            if sys.platform == "win32":
                os.startfile(output_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", output_dir])
            else:
                subprocess.Popen(["xdg-open", output_dir])
        except Exception as e:
            print(f"Warning: Could not open folder: {e}")
