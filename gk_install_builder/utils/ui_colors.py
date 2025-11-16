"""
UI color utilities for Store-Install-Builder
"""
import customtkinter as ctk


def get_theme_colors():
    """
    Get theme-aware colors based on current CustomTkinter theme and appearance mode.

    Returns:
        dict: Dictionary of color values for various UI elements
    """
    theme = ctk.ThemeManager.theme
    mode = ctk.get_appearance_mode()
    pick = lambda light, dark: light if mode == "Light" else dark

    # Extract base colors from theme
    base_bg = pick(*theme["CTkFrame"]["fg_color"]) if isinstance(theme.get("CTkFrame", {}).get("fg_color"), (list, tuple)) else theme.get("CTkFrame", {}).get("fg_color", "transparent")
    label_fg = pick(*theme["CTkLabel"]["text_color"]) if isinstance(theme.get("CTkLabel", {}).get("text_color"), (list, tuple)) else theme.get("CTkLabel", {}).get("text_color", None)
    btn_fg = pick(*theme["CTkButton"]["fg_color"]) if isinstance(theme.get("CTkButton", {}).get("fg_color"), (list, tuple)) else theme.get("CTkButton", {}).get("fg_color", None)
    btn_hover = pick(*theme["CTkButton"]["hover_color"]) if isinstance(theme.get("CTkButton", {}).get("hover_color"), (list, tuple)) else theme.get("CTkButton", {}).get("hover_color", None)
    entry_bg = pick(*theme["CTkEntry"]["fg_color"]) if isinstance(theme.get("CTkEntry", {}).get("fg_color"), (list, tuple)) else theme.get("CTkEntry", {}).get("fg_color", None)
    entry_border = pick(*theme["CTkEntry"]["border_color"]) if isinstance(theme.get("CTkEntry", {}).get("border_color"), (list, tuple)) else theme.get("CTkEntry", {}).get("border_color", None)

    # Build color dictionary
    return {
        'header_bg': base_bg,
        'path_bg': base_bg,
        'title_accent': label_fg,
        'muted_text': label_fg,
        'card_bg': base_bg,
        'primary': btn_fg,
        'primary_hover': btn_hover,
        'panel_bg': base_bg,
        'toolbar_bg': base_bg,
        'nav_btn': btn_fg,
        'nav_btn_hover': btn_hover,
        'nav_btn_disabled': ("#1E293B" if mode == "Dark" else "#D1D5DB"),
        'breadcrumb_bg': ("#1E293B" if mode == "Dark" else "#F1F5F9"),
        'breadcrumb_text': label_fg,
        'list_bg': base_bg,
        'list_fg': label_fg,
        'list_sel_bg': ("#334155" if mode == "Dark" else "#E2E8F0"),
        'list_sel_fg': label_fg,
        'menu_bg': base_bg,
        'menu_fg': label_fg,
        'menu_active_bg': ("#334155" if mode == "Dark" else "#E2E8F0"),
        'warning_text': ("#B45309", "#FF9E3D"),
        'status_badge_disconnected': ("#EF4444", "#FF6B6B"),
        'status_badge_warning': ("#F59E0B", "#F59E0B"),
        'status_badge_ok': ("#10B981", "#2ECC71"),
        'entry_bg': entry_bg,
        'entry_border': entry_border,
        'label_text': label_fg,
        'secondary_text': label_fg,
        'border_color': ("#334155" if mode == "Dark" else "#E2E8F0"),
        'separator_color': ("#1E293B" if mode == "Dark" else "#F1F5F9"),
    }
