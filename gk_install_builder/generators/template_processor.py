"""
Template processing functions for hostname regex replacement

This module contains functions for processing PowerShell and Bash templates,
specifically for replacing hostname detection regex patterns.
"""


import re


def replace_hostname_regex_powershell(template_content, custom_regex, add_disabled_message=False):
    """
    Replace the hostname detection regex in PowerShell template
    
    Args:
        template_content: The PowerShell template content
        custom_regex: Custom regex pattern to use for hostname detection
        add_disabled_message: Whether to add a disabled message
        
    Returns:
        Modified template content
    """
    # The pattern to find in the PowerShell template
    # Updated to match single quotes used in the actual template
    pattern = r"if \(\$hs -match '([^']+)'\) \{"

    # Use a function for the first replacement to avoid escape sequence issues
    def hostname_replacement(match):
        # Sanitize the regex for PowerShell single quotes
        safe_regex = custom_regex.replace("'", "''")
        if add_disabled_message:
            # Add informative message before the hostname detection
            return f'Write-Host "Hostname detection is disabled in configuration - skipping hostname detection" -ForegroundColor Yellow\n        if ($hs -match \'{safe_regex}\') {{'
        else:
            return f"if ($hs -match '{safe_regex}') {{"

    # Replace in the template using the function
    modified_content = re.sub(pattern, hostname_replacement, template_content)
    
    # Also update the validation regex for workstation ID
    # Find the validation pattern - now using the exact pattern from the GKInstall.ps1
    ws_validation_pattern = r"\$workstationId -match '\^\\d\{3\}\$'"
    
    # Use a function for replacement to avoid escape sequence issues
    def ws_replacement(match):
        return r"$workstationId -match '^\d+$'"

    # Replace in the template using the function
    modified_content = re.sub(ws_validation_pattern, ws_replacement, modified_content)
    
    return modified_content


def replace_hostname_regex_bash(template_content, custom_regex, add_disabled_message=False):
    """
    Replace the hostname detection regex in Bash template using direct string substitution
    
    Args:
        template_content: The Bash template content
        custom_regex: Custom regex pattern to use for hostname detection
        add_disabled_message: Whether to add a disabled message
        
    Returns:
        Modified template content
    """
    print(f"Attempting bash hostname regex replacement with: {custom_regex}")

    # The exact line we need to change from the template file
    target_line = '    if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]]; then'
    if add_disabled_message:
        # Add informative message before the hostname detection
        replacement_line = f'    echo "Hostname detection is disabled in configuration - skipping hostname detection"\n    if [[ "$hs" =~ {custom_regex} ]]; then'
    else:
        replacement_line = f'    if [[ "$hs" =~ {custom_regex} ]]; then'
    
    # Check if the target line exists
    if target_line in template_content:
        print(f"Found exact target line in template: {target_line}")
        modified_content = template_content.replace(target_line, replacement_line)
        print(f"Replaced with: {replacement_line}")
        
        # Also replace the workstation ID validation pattern if present
        ws_pattern = '[[ "$workstationId" =~ ^[0-9]{3}$ ]]'
        ws_replacement = '[[ "$workstationId" =~ ^[0-9]+$ ]]'
        if ws_pattern in modified_content:
            modified_content = modified_content.replace(ws_pattern, ws_replacement)
            print(f"Also updated workstation validation pattern")
        
        return modified_content
    else:
        # Fallback - try with different spacing/indentation
        print("Exact line not found, trying with flexible spacing...")
        
        # Create a list of possible variations with different spacing/indentation
        variations = [
            'if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]]; then',
            '  if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]]; then',
            '    if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]]; then',
            '      if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]]; then',
            'if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]];then',
            '  if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]];then',
            '    if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]];then',
            '      if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]];then'
        ]
        
        for variant in variations:
            if variant in template_content:
                print(f"Found variant: {variant}")
                # Calculate indentation from the found variant
                indent = ""
                for char in variant:
                    if char == ' ':
                        indent += ' '
                    else:
                        break
                
                # Create replacement with same indentation
                variant_replacement = f"{indent}if [[ \"$hs\" =~ {custom_regex} ]]; then"
                modified_content = template_content.replace(variant, variant_replacement)
                print(f"Replaced with: {variant_replacement}")
                
                # Also update workstation ID pattern
                ws_pattern = '[[ "$workstationId" =~ ^[0-9]{3}$ ]]'
                ws_replacement = '[[ "$workstationId" =~ ^[0-9]+$ ]]'
                if ws_pattern in modified_content:
                    modified_content = modified_content.replace(ws_pattern, ws_replacement)
                    print(f"Also updated workstation validation pattern")
                
                return modified_content
        
        # If we still haven't found the line, try a deeper search
        print("No variants found. Trying to find just the regex pattern...")
        regex_pattern = "([^-]+)-([0-9]+)$"
        if regex_pattern in template_content:
            print(f"Found regex pattern: {regex_pattern}")
            modified_content = template_content.replace(regex_pattern, custom_regex)
            print(f"Replaced regex pattern with: {custom_regex}")
            
            # Also update workstation ID pattern
            ws_pattern = "^[0-9]{3}$"
            ws_replacement = "^[0-9]+$"
            if ws_pattern in modified_content:
                modified_content = modified_content.replace(ws_pattern, ws_replacement)
                print(f"Also updated workstation validation pattern")
            
            return modified_content
        
        # Last resort - return the original template
        print("Warning: Could not find any matching patterns to replace in bash template")
        return template_content
