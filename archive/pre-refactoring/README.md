# Pre-Refactoring Archive

This folder contains the original code from before the Detection Settings refactoring.

## Files

- `main.py.old` - Original main.py file before refactoring (6,845 lines)
  - Source: Git commit 60ac733
  - Date: Before Detection Settings dialog extraction

## Refactoring Summary

The refactoring reduced main.py from 6,845 lines to 1,370 lines by extracting the Detection Settings dialog into:
- `gk_install_builder/dialogs/detection_settings.py`

## Changes Made

- Extracted Environment Detection tab
- Extracted File Detection tab
- Extracted Hostname Detection tab
- Implemented regex testing functionality
- Added 2-group/3-group pattern toggle
- Added platform-specific default paths
- Added notification popups for pattern changes
- Fixed automatic pattern updates when toggling environment detection

All 69 unit tests continue to pass after the refactoring.
