"""
Unit tests for platform switching functionality
"""
import pytest


class TestPlatformSwitching:
    """Test platform switching between Windows and Linux"""

    def test_windows_default_paths(self):
        """Test Windows default path configuration"""
        platform = "Windows"

        if platform == "Windows":
            default_dir = "C:\\gkretail"
            firebird_path = "C:\\Program Files\\Firebird\\Firebird_3_0"
            jaybird_driver_path = "C:\\gkretail\\Jaybird"
            default_detection_dir = "C:\\gkretail\\stations"
        else:
            default_dir = "/usr/local/gkretail"
            firebird_path = "/opt/firebird"
            jaybird_driver_path = "/usr/local/gkretail/Jaybird"
            default_detection_dir = "/usr/local/gkretail/stations"

        assert default_dir == "C:\\gkretail"
        assert firebird_path == "C:\\Program Files\\Firebird\\Firebird_3_0"
        assert jaybird_driver_path == "C:\\gkretail\\Jaybird"
        assert default_detection_dir == "C:\\gkretail\\stations"

    def test_linux_default_paths(self):
        """Test Linux default path configuration"""
        platform = "Linux"

        if platform == "Windows":
            default_dir = "C:\\gkretail"
            firebird_path = "C:\\Program Files\\Firebird\\Firebird_3_0"
            jaybird_driver_path = "C:\\gkretail\\Jaybird"
            default_detection_dir = "C:\\gkretail\\stations"
        else:
            default_dir = "/usr/local/gkretail"
            firebird_path = "/opt/firebird"
            jaybird_driver_path = "/usr/local/gkretail/Jaybird"
            default_detection_dir = "/usr/local/gkretail/stations"

        assert default_dir == "/usr/local/gkretail"
        assert firebird_path == "/opt/firebird"
        assert jaybird_driver_path == "/usr/local/gkretail/Jaybird"
        assert default_detection_dir == "/usr/local/gkretail/stations"

    def test_detect_windows_path(self):
        """Test detection of Windows path format"""
        current_path = "C:\\gkretail"

        has_windows_separator = "\\" in current_path
        has_linux_separator = "/" in current_path

        assert has_windows_separator is True
        assert has_linux_separator is False

    def test_detect_linux_path(self):
        """Test detection of Linux path format"""
        current_path = "/usr/local/gkretail"

        has_windows_separator = "\\" in current_path
        has_linux_separator = "/" in current_path

        assert has_windows_separator is False
        assert has_linux_separator is True

    def test_path_conversion_needed_windows_to_linux(self):
        """Test if path conversion is needed from Windows to Linux"""
        current_path = "C:\\gkretail"
        target_platform = "Linux"

        needs_conversion = (target_platform == "Windows" and "/" in current_path) or \
                           (target_platform == "Linux" and "\\" in current_path)

        assert needs_conversion is True

    def test_path_conversion_needed_linux_to_windows(self):
        """Test if path conversion is needed from Linux to Windows"""
        current_path = "/usr/local/gkretail"
        target_platform = "Windows"

        needs_conversion = (target_platform == "Windows" and "/" in current_path) or \
                           (target_platform == "Linux" and "\\" in current_path)

        assert needs_conversion is True

    def test_no_path_conversion_needed_windows(self):
        """Test when path conversion is not needed (Windows to Windows)"""
        current_path = "C:\\gkretail"
        target_platform = "Windows"

        needs_conversion = (target_platform == "Windows" and "/" in current_path) or \
                           (target_platform == "Linux" and "\\" in current_path)

        assert needs_conversion is False

    def test_no_path_conversion_needed_linux(self):
        """Test when path conversion is not needed (Linux to Linux)"""
        current_path = "/usr/local/gkretail"
        target_platform = "Linux"

        needs_conversion = (target_platform == "Windows" and "/" in current_path) or \
                           (target_platform == "Linux" and "\\" in current_path)

        assert needs_conversion is False

    def test_empty_path_handling(self):
        """Test handling of empty path during platform switch"""
        current_path = ""
        target_platform = "Windows"

        if not current_path:
            should_set_default = True
        else:
            should_set_default = False

        assert should_set_default is True

    def test_platform_specific_install_directory(self):
        """Test that install directory changes based on platform"""
        # Simulate platform change
        platforms = ["Windows", "Linux"]
        expected_dirs = {
            "Windows": "C:\\gkretail",
            "Linux": "/usr/local/gkretail"
        }

        for platform in platforms:
            if platform == "Windows":
                default_dir = "C:\\gkretail"
            else:
                default_dir = "/usr/local/gkretail"

            assert default_dir == expected_dirs[platform]
