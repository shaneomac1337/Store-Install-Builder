"""
UI helper functions for Store-Install-Builder
"""
import sys


def bind_mousewheel_to_frame(frame):
    """
    Bind mousewheel events to a frame to enable scrolling in Linux.

    Args:
        frame: The frame to add scrolling to (must be a CTkScrollableFrame)
    """
    # Skip if not a CTkScrollableFrame
    if not hasattr(frame, '_parent_canvas'):
        return

    # For Linux, we need special handling for Button-4 and Button-5 events
    if sys.platform.startswith('linux'):
        # Find the root window that contains this frame
        root = frame.winfo_toplevel()

        # Create a unique tag for this frame to avoid conflicts between windows
        frame_id = str(id(frame))
        scroll_tag = f"scroll_{frame_id}"

        # Function for scrolling up
        def _on_mousewheel_up(event):
            # Get the window under the cursor
            widget_under_cursor = event.widget.winfo_containing(event.x_root, event.y_root)

            # Check if the widget is in the same window hierarchy as our frame
            current_widget = widget_under_cursor
            while current_widget:
                if current_widget == frame or current_widget == frame._parent_canvas:
                    frame._parent_canvas.yview_scroll(-1, "units")
                    return "break"
                current_widget = current_widget.master

            # If we're not in the right window, don't handle the event
            return

        # Function for scrolling down
        def _on_mousewheel_down(event):
            # Get the window under the cursor
            widget_under_cursor = event.widget.winfo_containing(event.x_root, event.y_root)

            # Check if the widget is in the same window hierarchy as our frame
            current_widget = widget_under_cursor
            while current_widget:
                if current_widget == frame or current_widget == frame._parent_canvas:
                    frame._parent_canvas.yview_scroll(1, "units")
                    return "break"
                current_widget = current_widget.master

            # If we're not in the right window, don't handle the event
            return

        # Store event handlers
        if not hasattr(frame, '_scroll_handlers'):
            frame._scroll_handlers = {}
        frame._scroll_handlers[scroll_tag] = (_on_mousewheel_up, _on_mousewheel_down)

        # Bind to the toplevel window containing this frame, but not globally
        root.bind("<Button-4>", _on_mousewheel_up, add="+")
        root.bind("<Button-5>", _on_mousewheel_down, add="+")

        # Create cleanup function to remove bindings when window is destroyed
        def _cleanup_bindings():
            if hasattr(root, "bind"):  # Check if root still exists
                try:
                    root.unbind("<Button-4>", _on_mousewheel_up)
                    root.unbind("<Button-5>", _on_mousewheel_down)
                except:
                    pass

        # Bind cleanup to window destruction
        root.bind("<Destroy>", lambda e: _cleanup_bindings(), add="+")
    else:
        # Windows and macOS use MouseWheel event
        def _on_mousewheel(event):
            # Get the window under the cursor
            widget_under_cursor = event.widget.winfo_containing(event.x_root, event.y_root)

            # Check if the widget is in the same window hierarchy as our frame
            current_widget = widget_under_cursor
            while current_widget:
                if current_widget == frame or current_widget == frame._parent_canvas:
                    # Increase scrolling speed on Windows by using a larger multiplier
                    if sys.platform == 'win32':
                        # Changed from 20 to 5 for much faster scrolling on Windows
                        frame._parent_canvas.yview_scroll(int(-1*(event.delta/5)), "units")
                    else:
                        # Keep original behavior for other platforms
                        frame._parent_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                    return "break"
                current_widget = current_widget.master

            # If we're not in the right window, don't handle the event
            return

        # Store event handler
        frame_id = str(id(frame))
        scroll_tag = f"scroll_{frame_id}"
        if not hasattr(frame, '_scroll_handlers'):
            frame._scroll_handlers = {}
        frame._scroll_handlers[scroll_tag] = _on_mousewheel

        # Find the root window that contains this frame
        root = frame.winfo_toplevel()

        # Bind to the toplevel window
        root.bind("<MouseWheel>", _on_mousewheel, add="+")

        # Create cleanup function
        def _cleanup_bindings():
            if hasattr(root, "bind"):  # Check if root still exists
                try:
                    root.unbind("<MouseWheel>", _on_mousewheel)
                except:
                    pass

        # Bind cleanup to window destruction
        root.bind("<Destroy>", lambda e: _cleanup_bindings(), add="+")
