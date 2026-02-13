"""
Version management utilities

This module contains functions for determining component versions
based on system types and configuration settings.
"""


def get_component_version(system_type, config):
    """
    Determine the correct version for a component based on its system type

    Args:
        system_type: The system type string (e.g., "GKR-OPOS-CLOUD", "CSE-wdm")
        config: Configuration dictionary containing version settings

    Returns:
        str: The version string to use for the component

    Notes:
        - If use_version_override is False, always returns default version
        - Matches system_type against known types and returns corresponding version
        - Falls back to default version if no match found
    """
    # Get version information from config
    default_version = config.get("version", "v1.0.0")
    use_version_override = config.get("use_version_override", False)

    # If version override is disabled, always use the default version
    if not use_version_override:
        return default_version

    # If system type is empty, use default version
    if not system_type or system_type == "":
        return default_version

    # Print debug information
    print(f"\nDetermining version for system type: {system_type}")
    print(f"Version override enabled: {use_version_override}")

    # Match against system type using substring matching to support any project code prefix
    # (e.g., GKR-sh-cloud, CSE-sh-cloud, ABC-sh-cloud all match StoreHub)
    st = system_type.upper()

    # Check OneX POS first since it also contains "OPOS"
    if "OPOS-ONEX" in st:
        version = config.get("onex_pos_version", default_version)
        print(f"Matched OneX POS system type, using version: {version}")
        return version
    elif "OPOS" in st:
        version = config.get("pos_version", default_version)
        print(f"Matched POS system type, using version: {version}")
        return version
    elif "WDM" in st:
        version = config.get("wdm_version", default_version)
        print(f"Matched WDM system type, using version: {version}")
        return version
    elif "FLOWSERVICE" in st:
        version = config.get("flow_service_version", default_version)
        print(f"Matched Flow Service system type, using version: {version}")
        return version
    elif "LPS-LPA" in st:
        version = config.get("lpa_service_version", default_version)
        print(f"Matched LPA Service system type, using version: {version}")
        return version
    elif "SH-CLOUD" in st:
        version = config.get("storehub_service_version", default_version)
        print(f"Matched StoreHub Service system type, using version: {version}")
        return version
    elif "RESOURCE-CACHE-SERVICE" in st:
        version = config.get("rcs_version", default_version)
        print(f"Matched RCS system type, using version: {version}")
        return version
    else:
        print(f"No match found for system type, using default version: {default_version}")
        return default_version
