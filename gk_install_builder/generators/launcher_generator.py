"""
Launcher template generation functions

This module contains functions for generating launcher configuration files
with custom settings from the project configuration.
"""

import os


def normalize_firebird_path_for_linux(firebird_server_path):
    """
    Normalize Firebird server path for Linux

    Args:
        firebird_server_path: The Firebird server path from config

    Returns:
        Normalized Linux path
    """
    # Start with a completely clean approach
    # First, extract just the path parts we need
    path_parts = []

    # Split by slashes and process each part
    for part in firebird_server_path.replace('\\', '/').split('/'):
        if part and part != "firebird":
            path_parts.append(part)

    # For Linux, we want a path like /opt/firebird
    # Ensure 'opt' is in the path
    if 'opt' not in path_parts:
        path_parts = ['opt'] + path_parts

    # Build the path with a leading slash and no trailing slash
    firebird_server_path = "/" + "/".join(path_parts)

    # Finally, ensure it ends with /firebird
    if not firebird_server_path.endswith('/firebird'):
        firebird_server_path = firebird_server_path.rstrip('/') + '/firebird'

    return firebird_server_path


def apply_settings_to_template(template_content, settings, filename):
    """
    Apply custom settings to a launcher template

    Args:
        template_content: The template content
        settings: Dictionary of settings to apply
        filename: The launcher template filename (for logging)

    Returns:
        Modified template content
    """
    if not settings:
        print(f"No settings to apply for {filename}, using default template")
        return template_content

    # Update the template with the settings
    lines = template_content.strip().split('\n')
    new_lines = []

    for line in lines:
        if line.startswith('#') or not line.strip():
            new_lines.append(line)
            continue

        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()

            # If this key has a setting
            if key in settings:
                # Update the value
                new_value = settings[key]
                print(f"Setting {key} to {new_value} in {filename}")
                new_lines.append(f"{key}={new_value}")
            else:
                # Keep the line as is
                new_lines.append(line)
        else:
            # Keep the line as is
            new_lines.append(line)

    return '\n'.join(new_lines)


def generate_launcher_templates(launchers_dir, config, launcher_templates):
    """
    Generate launcher templates with custom settings from config

    Args:
        launchers_dir: Directory where launcher templates will be created
        config: Configuration dictionary with launcher settings
        launcher_templates: Dictionary mapping filenames to template content

    Returns:
        None (writes files to disk)
    """
    # Get settings from config
    pos_settings = config.get("pos_launcher_settings", {})
    onex_pos_settings = config.get("onex_pos_launcher_settings", {})
    wdm_settings = config.get("wdm_launcher_settings", {})
    flow_service_settings = config.get("flow_service_launcher_settings", {})
    lpa_service_settings = config.get("lpa_service_launcher_settings", {})
    storehub_service_settings = config.get("storehub_service_launcher_settings", {})
    rcs_service_settings = config.get("rcs_service_launcher_settings", {})

    # Print debug info
    print("Using launcher settings from config:")
    print(f"POS settings: {pos_settings}")
    print(f"ONEX-POS settings: {onex_pos_settings}")
    print(f"WDM settings: {wdm_settings}")
    print(f"FLOW-SERVICE settings: {flow_service_settings}")
    print(f"LPA-SERVICE settings: {lpa_service_settings}")
    print(f"STOREHUB-SERVICE settings: {storehub_service_settings}")
    print(f"RCS-SERVICE settings: {rcs_service_settings}")

    # Define template files
    template_files = {
        "launcher.pos.template": pos_settings,
        "launcher.onex-pos.template": onex_pos_settings,
        "launcher.wdm.template": wdm_settings,
        "launcher.flow-service.template": flow_service_settings,
        "launcher.lpa-service.template": lpa_service_settings,
        "launcher.storehub-service.template": storehub_service_settings,
        "launcher.rcs-service.template": rcs_service_settings
    }

    # We'll use templates directly from code instead of trying to find them on disk
    # This avoids path resolution issues when packaged as executable
    for filename, settings in template_files.items():
        # Get the template content
        template_content = launcher_templates.get(filename, "")
        if not template_content:
            print(f"Warning: No template found for {filename}")
            continue

        # Create template path
        template_path = os.path.join(launchers_dir, filename)

        # Get Firebird server path from config for direct replacement
        firebird_server_path = config.get("firebird_server_path", "")
        # Get the platform from config
        platform_type = config.get("platform", "Windows")

        # Process specific replacements for StoreHub Service
        if filename == "launcher.storehub-service.template" and firebird_server_path:
            # Ensure the path is properly formatted for Linux
            if platform_type.lower() == "linux":
                firebird_server_path = normalize_firebird_path_for_linux(firebird_server_path)
                print(f"Normalized Firebird path for Linux: {firebird_server_path}")

            print(f"Replacing @FIREBIRD_SERVER_PATH@ with {firebird_server_path} in {filename}")
            template_content = template_content.replace("@FIREBIRD_SERVER_PATH@", firebird_server_path)

        # Apply settings to the template
        template_content = apply_settings_to_template(template_content, settings, filename)

        # Write the template to the output file
        try:
            with open(template_path, 'w') as f:
                f.write(template_content)
            print(f"Generated launcher template: {filename}")
        except Exception as e:
            print(f"Error generating launcher template {filename}: {str(e)}")


def create_default_template(launchers_dir, filename):
    """
    Create a default launcher template file

    Args:
        launchers_dir: Directory where template will be created
        filename: Name of the template file to create

    Returns:
        None (writes file to disk)
    """
    template_content = ""

    if filename == "launcher.pos.template":
        template_content = """# Launcher defaults for POS
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationJmxPort=
updaterJmxPort=
createShortcuts=0
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
hardware_package_local=
"""
    elif filename == "launcher.onex-pos.template":
        template_content = """# Launcher defaults for OneX POS Client
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationJmxPort=
updaterJmxPort=
createShortcuts=0
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
userInterface_package_local=@UI_PACKAGE@
hardware_package_local=
"""
    elif filename == "launcher.wdm.template":
        template_content = """# Launcher defaults for WDM
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8080
applicationServerHttpsPort=8443
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
    elif filename == "launcher.flow-service.template":
        template_content = """# Launcher defaults for Flow Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
    elif filename == "launcher.lpa-service.template":
        template_content = """# Launcher defaults for LPA Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
    elif filename == "launcher.storehub-service.template":
        template_content = """# Launcher defaults for StoreHub Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
applicationJmsPort=7001
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
firebirdServerPath=@FIREBIRD_SERVER_PATH@
firebird_driver_path_local=@FIREBIRD_DRIVER_PATH_LOCAL@
firebirdServerPort=3050
firebirdServerUser=SYSDBA
firebirdServerPassword=masterkey
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""
    elif filename == "launcher.rcs-service.template":
        template_content = """# Launcher defaults for RCS Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""

    # Write the template to the file
    file_path = os.path.join(launchers_dir, filename)
    try:
        with open(file_path, 'w') as f:
            f.write(template_content)
        print(f"Created default template: {filename}")
    except Exception as e:
        print(f"Error creating default template {filename}: {str(e)}")
