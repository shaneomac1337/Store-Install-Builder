"""
File operation utilities for ProjectGenerator

This module contains file and directory operation functions extracted
from generator.py to improve modularity and testability.
"""

import os
import shutil


def create_directory_structure(output_dir, helper_structure):
    """
    Create the project directory structure
    
    Args:
        output_dir: The output directory path
        helper_structure: Dictionary defining the directory structure
    """
    for dir_name in helper_structure.keys():
        os.makedirs(os.path.join(output_dir, "helper", dir_name), exist_ok=True)


def copy_certificate(output_dir, config):
    """
    Copy SSL certificate to output directory if it exists
    
    Args:
        output_dir: The output directory path
        config: Configuration dictionary containing certificate_path
        
    Returns:
        True if certificate was copied successfully, False otherwise
    """
    try:
        cert_path = config.get("certificate_path", "")
        if cert_path and os.path.exists(cert_path):
            # Copy certificate to output directory with the same name
            cert_filename = os.path.basename(cert_path)
            dest_path = os.path.join(output_dir, cert_filename)
            shutil.copy2(cert_path, dest_path)
            print(f"Copied certificate from {cert_path} to {dest_path}")
            
            return True
    except Exception as e:
        print(f"Warning: Failed to copy certificate: {str(e)}")

    return False


def write_installation_script(output_path, template_content, platform, output_filename):
    """
    Write installation script with platform-specific line endings and encoding

    Args:
        output_path: Full path where the script will be written
        template_content: The processed template content to write
        platform: Platform string ("Windows" or "Linux")
        output_filename: Name of the output file (for logging)

    Returns:
        None (writes file to disk)

    Notes:
        - Windows: Uses CRLF line endings and UTF-8 BOM for PowerShell 5.1 compatibility
        - Linux: Uses LF line endings and sets executable permissions
    """
    # Write the modified template to the output file
    # PowerShell 5.1 requires proper Windows line endings (CRLF) and UTF-8 BOM for Unicode support
    if platform == "Windows":
        # For Windows: ensure consistent CRLF line endings for PowerShell 5.1 compatibility
        # First normalize all line endings to LF, then convert to CRLF
        template_content = template_content.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
        # Write with binary mode to ensure exact byte output with UTF-8 BOM
        with open(output_path, 'wb') as f:
            # Add UTF-8 BOM for PowerShell 5.1 to properly detect encoding
            f.write(b'\xef\xbb\xbf')
            f.write(template_content.encode('utf-8'))
    else:
        # For Linux: use LF line endings
        template_content = template_content.replace('\r\n', '\n').replace('\r', '\n')
        with open(output_path, 'w', newline='\n', encoding='utf-8') as f:
            f.write(template_content)

    # For Linux scripts, make the file executable
    if platform == "Linux":
        try:
            os.chmod(output_path, 0o755)  # rwxr-xr-x
            print(f"Made {output_filename} executable")
        except Exception as e:
            print(f"Warning: Failed to make {output_filename} executable: {e}")

    print(f"Successfully generated {output_filename} at {output_path}")


def determine_gk_install_paths(platform, output_dir, script_dir):
    """
    Determine template and output paths for GKInstall script based on platform

    Args:
        platform: Platform string ("Windows" or "Linux")
        output_dir: Directory where the output script will be written
        script_dir: Directory where the generator script is located (for finding templates)

    Returns:
        tuple: (template_path, output_path, template_filename, output_filename)
            - template_path: Absolute path to the template file
            - output_path: Absolute path where the script will be written
            - template_filename: Name of the template file
            - output_filename: Name of the output script file

    Notes:
        - Windows: Uses GKInstall.ps1.template -> GKInstall.ps1
        - Linux: Uses GKInstall.sh.template -> GKInstall.sh
    """
    # Determine template and output filenames based on platform
    if platform == "Windows":
        template_filename = "GKInstall.ps1.template"
        output_filename = "GKInstall.ps1"
    else:  # Linux
        template_filename = "GKInstall.sh.template"
        output_filename = "GKInstall.sh"

    # Use absolute paths for template and output
    template_path = os.path.join(script_dir, "templates", template_filename)
    output_path = os.path.join(output_dir, output_filename)

    return template_path, output_path, template_filename, output_filename
