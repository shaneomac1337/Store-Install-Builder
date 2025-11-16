"""
Tooltip utilities for Store-Install-Builder
"""
import customtkinter as ctk


class Tooltip:
    """
    Create tooltips for widgets with configurable delay and styling.
    """

    def __init__(self, widget, text, delay=300, parent_window=None):
        """
        Initialize tooltip for a widget.

        Args:
            widget: The widget to attach the tooltip to
            text: The tooltip text to display
            delay: Delay in milliseconds before showing tooltip (default: 300ms)
            parent_window: Parent window for the tooltip (default: widget's toplevel)
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.parent_window = parent_window or widget.winfo_toplevel()

        self.tooltip_id = None
        self.tooltip_window = None

        # Bind events
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)

        # Bind to window close for cleanup
        self.parent_window.bind("<Destroy>", self._safe_leave, add="+")

    def _show_tooltip(self, x, y):
        """Display the tooltip at the specified position"""
        # If there's already a tooltip showing, destroy it first
        if self.tooltip_window is not None:
            try:
                self.tooltip_window.destroy()
            except:
                pass

        # Create a toplevel window for the tooltip
        self.tooltip_window = ctk.CTkToplevel(self.parent_window)
        self.tooltip_window.wm_overrideredirect(True)  # Remove window decorations
        self.tooltip_window.wm_geometry(f"+{x+15}+{y+10}")
        self.tooltip_window.attributes("-topmost", True)  # Keep tooltip on top

        # Create a label with the tooltip text
        label = ctk.CTkLabel(
            self.tooltip_window,
            text=self.text,
            corner_radius=6,
            fg_color=("#333333", "#666666"),  # Dark background
            text_color=("#FFFFFF", "#FFFFFF"),  # White text
            padx=10,
            pady=5,
            wraplength=300
        )
        label.pack()

        # Store the tooltip reference in the widget
        self.widget._tooltip_window = self.tooltip_window

    def _on_enter(self, event):
        """Handle mouse entering the widget"""
        # Cancel any existing scheduled tooltip
        if self.tooltip_id is not None:
            self.widget.after_cancel(self.tooltip_id)
            self.tooltip_id = None

        # Schedule new tooltip with delay
        self.tooltip_id = self.widget.after(
            self.delay,
            lambda: self._show_tooltip(event.x_root, event.y_root)
        )

    def _on_leave(self, event):
        """Handle mouse leaving the widget"""
        # Cancel any scheduled tooltip
        if self.tooltip_id is not None:
            self.widget.after_cancel(self.tooltip_id)
            self.tooltip_id = None

        # Destroy any existing tooltip
        if self.tooltip_window is not None:
            try:
                self.tooltip_window.destroy()
            except:
                pass
            self.tooltip_window = None

        # Also check for the old tooltip attribute for backward compatibility
        if hasattr(self.widget, "_tooltip_window"):
            try:
                self.widget._tooltip_window.destroy()
            except:
                pass
            try:
                delattr(self.widget, "_tooltip_window")
            except:
                pass

    def _safe_leave(self, event):
        """Safely handle leave event during window destruction"""
        try:
            self._on_leave(event)
        except:
            pass


def create_tooltip(widget, text, delay=300, parent_window=None):
    """
    Create a tooltip for a widget (convenience function).

    Args:
        widget: The widget to attach the tooltip to
        text: The tooltip text to display
        delay: Delay in milliseconds before showing tooltip (default: 300ms)
        parent_window: Parent window for the tooltip (default: widget's toplevel)

    Returns:
        Tooltip instance
    """
    return Tooltip(widget, text, delay, parent_window)
