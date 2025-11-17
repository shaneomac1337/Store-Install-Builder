"""
Environment setup utilities

This module contains functions for setting up environment variables
needed by the installation scripts.
"""

import os


def setup_firebird_environment_variables(config, platform):
    """
    Set up Firebird-related environment variables

    Args:
        config: Configuration dictionary
        platform: Platform string ("Windows" or "Linux")

    Returns:
        None (sets environment variables as side effect)
    """
    # Set environment variable for Firebird server path
    firebird_server_path = config.get("firebird_server_path", "")
    if firebird_server_path:
        os.environ["FIREBIRD_SERVER_PATH"] = firebird_server_path
        print(f"Setting FIREBIRD_SERVER_PATH environment variable to: {firebird_server_path}")
    else:
        print("Warning: firebird_server_path is not set in config")

    # Set environment variable for Jaybird driver path
    firebird_driver_path_local = config.get("firebird_driver_path_local", "")
    if firebird_driver_path_local:
        os.environ["FIREBIRD_DRIVER_PATH_LOCAL"] = firebird_driver_path_local
        print(f"Setting FIREBIRD_DRIVER_PATH_LOCAL environment variable to: {firebird_driver_path_local}")
    else:
        # Set default paths based on platform
        if platform == "Windows":
            default_path = "C:\\gkretail\\Jaybird"
        else:
            default_path = "/usr/local/gkretail/Jaybird"
        os.environ["FIREBIRD_DRIVER_PATH_LOCAL"] = default_path
        print(f"Setting default FIREBIRD_DRIVER_PATH_LOCAL to: {default_path}")
