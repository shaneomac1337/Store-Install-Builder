"""
Generator-specific fixtures and utilities for testing Phase 0

This module provides helper functions, assertions, and utilities
specifically for testing the ProjectGenerator class.
"""

import json
import os
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock


# ============================================================================
# Configuration Helpers
# ============================================================================

def load_config_from_file(config_name: str) -> Dict:
    """
    Load a configuration file from tests/fixtures/configs/

    Args:
        config_name: Name of config file (e.g., 'minimal_windows.json')

    Returns:
        Dictionary with configuration data
    """
    fixtures_dir = Path(__file__).parent
    config_path = fixtures_dir / "configs" / config_name

    with open(config_path, 'r') as f:
        return json.load(f)


def create_config(**overrides) -> Dict:
    """
    Create a configuration dictionary with specified overrides

    Args:
        **overrides: Key-value pairs to override default config

    Returns:
        Configuration dictionary
    """
    # Get platform from overrides or use default
    platform = overrides.get("platform", "Windows")

    # Set platform-specific defaults
    if platform == "Linux":
        base_install_dir = "/usr/local/gkretail"
        firebird_path = "/opt/firebird"
        jaybird_path = "/usr/local/gkretail/Jaybird"
    else:
        base_install_dir = "C:\\gkretail"
        firebird_path = "C:\\Program Files\\Firebird\\Firebird_3_0"
        jaybird_path = "C:\\gkretail\\Jaybird"

    default_config = {
        "platform": platform,
        "base_url": "test.cloud4retail.co",
        "base_install_dir": base_install_dir,
        "firebird_server_path": firebird_path,
        "jaybird_path": jaybird_path,
        "project_name": "Test Project",
        "version": "v1.0.0",
        "tenant_id": "001",
        "output_dir": "test_output",
        "ssl_password": "changeit",
        "system_type": "GKR-POS-CLOUD",
        "include_pos": False,
        "include_wdm": False,
        "include_flow_service": False,
        "include_lpa_service": False,
        "include_storehub_service": False,
        "use_hostname_detection": False,
        "use_file_detection": False,
        "installer_overrides_enabled": True,
        "installer_overrides_components": {
            "POS": True, "ONEX-POS": True, "WDM": True,
            "FLOW-SERVICE": True, "LPA-SERVICE": True,
            "STOREHUB-SERVICE": True, "RCS-SERVICE": True,
        },
        "installer_overrides_properties": {
            "check-alive": True,
            "start-application": False,
        },
        "certificate_path": "",
        "environments": [],
        "eh_launchpad_username": "1001",
        "eh_launchpad_password": "testpassword",
        "launchpad_oauth2": "testpass"
    }

    default_config.update(overrides)
    return default_config


#============================================================================
# Directory Structure Helpers
# ============================================================================

def verify_directory_structure(output_dir: Path, expected_subdirs: List[str]) -> bool:
    """
    Verify that expected subdirectories exist in output directory

    Args:
        output_dir: Path to output directory
        expected_subdirs: List of expected subdirectory names

    Returns:
        True if all subdirectories exist
    """
    for subdir in expected_subdirs:
        subdir_path = output_dir / subdir
        if not subdir_path.exists() or not subdir_path.is_dir():
            return False
    return True


def get_helper_subdirs() -> List[str]:
    """
    Get list of expected helper subdirectories created by _create_directory_structure()

    Note: "environments" is created separately by _generate_environments_json()

    Returns:
        List of helper subdirectory names
    """
    return [
        "launchers",
        "onboarding",
        "tokens",
        "init"
    ]


def verify_helper_structure(output_dir: Path) -> bool:
    """
    Verify that helper directory structure is correct

    Args:
        output_dir: Path to output directory

    Returns:
        True if helper structure is correct
    """
    helper_dir = output_dir / "helper"
    if not helper_dir.exists():
        return False

    return verify_directory_structure(helper_dir, get_helper_subdirs())


# ============================================================================
# File Content Helpers
# ============================================================================

def count_unreplaced_variables(content: str) -> int:
    """
    Count number of unreplaced @VARIABLE@ markers in content

    Args:
        content: File content to check

    Returns:
        Number of unreplaced variable markers
    """
    import re
    pattern = r'@[A-Z_]+@'
    matches = re.findall(pattern, content)
    return len(matches)


def get_unreplaced_variables(content: str) -> List[str]:
    """
    Get list of unreplaced @VARIABLE@ markers in content

    Args:
        content: File content to check

    Returns:
        List of unreplaced variable names
    """
    import re
    pattern = r'@([A-Z_]+)@'
    matches = re.findall(pattern, content)
    return matches


def verify_variable_replacement(content: str, variable: str, expected_value: str) -> bool:
    """
    Verify that a variable was replaced with expected value

    Args:
        content: File content to check
        variable: Variable name (without @ markers)
        expected_value: Expected replacement value

    Returns:
        True if variable was replaced correctly
    """
    marker = f"@{variable}@"
    return marker not in content and expected_value in content


# ============================================================================
# Template Helpers
# ============================================================================

def create_minimal_template(template_type: str = "powershell") -> str:
    """
    Create a minimal template for testing

    Args:
        template_type: Type of template ('powershell', 'bash', or 'launcher')

    Returns:
        Template content as string
    """
    if template_type == "powershell":
        return """# Test PowerShell Template
$BASE_URL = "@BASE_URL@"
$INSTALL_DIR = "@BASE_INSTALL_DIR@"
$VERSION = "@VERSION@"
$TENANT_ID = "@TENANT_ID@"
# HOSTNAME_ENV_DETECTION_PLACEHOLDER
"""
    elif template_type == "bash":
        return """#!/bin/bash
# Test Bash Template
BASE_URL="@BASE_URL@"
INSTALL_DIR="@BASE_INSTALL_DIR@"
VERSION="@VERSION@"
TENANT_ID="@TENANT_ID@"
# HOSTNAME_ENV_DETECTION_PLACEHOLDER
"""
    elif template_type == "launcher":
        return """{
  "component": "@COMPONENT_NAME@",
  "version": "@COMPONENT_VERSION@",
  "baseUrl": "@BASE_URL@"
}"""
    else:
        raise ValueError(f"Unknown template type: {template_type}")


def create_template_dir_with_files(tmp_path: Path) -> Path:
    """
    Create a template directory with all required template files

    Args:
        tmp_path: Temporary path (from pytest tmp_path fixture)

    Returns:
        Path to created template directory
    """
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    # Create PowerShell templates
    (template_dir / "GKInstall.ps1.template").write_text(create_minimal_template("powershell"))
    (template_dir / "onboarding.ps1.template").write_text(create_minimal_template("powershell"))
    (template_dir / "store-initialization.ps1.template").write_text(create_minimal_template("powershell"))

    # Create Bash templates
    (template_dir / "GKInstall.sh.template").write_text(create_minimal_template("bash"))
    (template_dir / "onboarding.sh.template").write_text(create_minimal_template("bash"))
    (template_dir / "store-initialization.sh.template").write_text(create_minimal_template("bash"))

    return template_dir


# ============================================================================
# Assertion Helpers
# ============================================================================

def assert_file_exists(file_path: Path, message: str = None):
    """
    Assert that a file exists

    Args:
        file_path: Path to file
        message: Optional custom error message

    Raises:
        AssertionError if file doesn't exist
    """
    if not file_path.exists():
        msg = message or f"Expected file does not exist: {file_path}"
        raise AssertionError(msg)


def assert_file_contains(file_path: Path, expected_content: str):
    """
    Assert that file contains expected content

    Args:
        file_path: Path to file
        expected_content: Content that should be in file

    Raises:
        AssertionError if content not found
    """
    assert_file_exists(file_path)

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if expected_content not in content:
        raise AssertionError(
            f"File {file_path} does not contain expected content: {expected_content}"
        )


def assert_no_unreplaced_variables(file_path: Path):
    """
    Assert that file has no unreplaced @VARIABLE@ markers

    Args:
        file_path: Path to file

    Raises:
        AssertionError if unreplaced variables found
    """
    assert_file_exists(file_path)

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    unreplaced = get_unreplaced_variables(content)
    if unreplaced:
        raise AssertionError(
            f"File {file_path} contains unreplaced variables: {', '.join(unreplaced)}"
        )


def assert_json_file_valid(file_path: Path):
    """
    Assert that file contains valid JSON

    Args:
        file_path: Path to JSON file

    Raises:
        AssertionError if JSON is invalid
    """
    assert_file_exists(file_path)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
    except json.JSONDecodeError as e:
        raise AssertionError(f"File {file_path} contains invalid JSON: {e}")


# ============================================================================
# Mock Helpers
# ============================================================================

def create_mock_generator(with_detection_manager: bool = True) -> Mock:
    """
    Create a mock ProjectGenerator for testing

    Args:
        with_detection_manager: Whether to include DetectionManager mock

    Returns:
        Mock ProjectGenerator instance
    """
    mock_gen = Mock()
    mock_gen.generate = Mock(return_value=True)
    mock_gen._show_error = Mock()
    mock_gen._show_success = Mock()
    mock_gen._show_info = Mock()

    if with_detection_manager:
        mock_gen.detection_manager = create_mock_detection_manager()

    return mock_gen


def create_mock_detection_manager() -> Mock:
    """
    Create a mock DetectionManager for testing

    Returns:
        Mock DetectionManager instance
    """
    mock = Mock()
    mock.is_detection_enabled.return_value = False
    mock.get_file_path.return_value = "C:\\gkretail\\stations\\POS.station"
    mock.get_base_directory.return_value = "C:\\gkretail"
    mock.detection_config = {
        "file_detection_enabled": True,
        "use_base_directory": True,
        "base_directory": "",
        "custom_filenames": {
            "POS": "POS.station",
            "WDM": "WDM.station",
            "FLOW-SERVICE": "FLOW-SERVICE.station",
            "LPA-SERVICE": "LPA.station",
            "STOREHUB-SERVICE": "SH.station"
        },
        "detection_files": {
            "POS": "",
            "WDM": "",
            "FLOW-SERVICE": "",
            "LPA-SERVICE": "",
            "STOREHUB-SERVICE": ""
        },
        "hostname_detection": {
            "windows_regex": r"^([0-9]{4})-([0-9]{3})$",
            "linux_regex": r"^([0-9]{4})-([0-9]{3})$",
            "test_hostname": "1234-101",
            "detect_environment": False,
            "env_group": 1,
            "store_group": 1,
            "workstation_group": 2
        }
    }
    return mock


# ============================================================================
# Expected Output Helpers
# ============================================================================

def get_expected_windows_files() -> List[str]:
    """Get list of expected files for Windows generation"""
    return [
        "GKInstall.ps1",
        "onboarding.ps1",
        "store-initialization.ps1"
    ]


def get_expected_linux_files() -> List[str]:
    """Get list of expected files for Linux generation"""
    return [
        "GKInstall.sh",
        "onboarding.sh",
        "store-initialization.sh"
    ]


def get_expected_helper_files() -> List[str]:
    """Get list of expected helper files"""
    return [
        "helper/tokens/basic_auth_password.txt",
        "helper/tokens/form_password.txt",
        "helper/init/get_store.json"
    ]


def verify_generated_output(output_dir: Path, platform: str) -> bool:
    """
    Verify that all expected files were generated

    Args:
        output_dir: Path to output directory
        platform: Platform type ('Windows' or 'Linux')

    Returns:
        True if all expected files exist
    """
    if platform == "Windows":
        expected_files = get_expected_windows_files()
    elif platform == "Linux":
        expected_files = get_expected_linux_files()
    else:
        return False

    for file_name in expected_files:
        file_path = output_dir / file_name
        if not file_path.exists():
            return False

    return True
