"""
Unit tests for installer.properties support in offline package creation.

Tests fetching, parsing, preferences building, and pre-selection logic.
"""

import pytest
from unittest.mock import MagicMock, patch
from gk_install_builder.generators.offline_package_helpers import (
    fetch_installer_properties,
    build_installer_preferences,
)


# --- Sample installer.properties content ---

SAMPLE_PROPERTIES_CONTENT = """# Auto-generated installer properties
java_version=17.0.16
onex_ui_mac=GKR-OPOS-ONEX-CLOUD/v5.29.0/onex-ui-5.29.0-mac.zip
onex_ui_windows=GKR-OPOS-ONEX-CLOUD/v5.29.0/onex-ui-5.29.0-windows.zip
onex_ui_linux=GKR-OPOS-ONEX-CLOUD/v5.29.0/onex-ui-5.29.0-linux.zip
java_mac=Java/zulujre-macosx_aarch64-17.0.16.tar.gz
java_windows=Java/zulujre-windows_x64-17.0.16.zip
java_linux=Java/zulujre-linux_x64-17.0.16.zip
installer_path=GKR-OPOS-ONEX-CLOUD/v5.29.0/onex-launcher-cloud-5.29.0-b11-installer.jar
"""


class TestFetchInstallerProperties:
    """Tests for fetch_installer_properties()."""

    def _make_mock_browser(self, file_list, file_content=""):
        """Create a mock DSGRestBrowser with predefined responses."""
        browser = MagicMock()
        browser.list_directories.return_value = file_list
        browser.get_file_url.return_value = "https://example.com/test/installer.properties"
        browser._get_headers.return_value = {"Authorization": "Bearer test"}

        mock_response = MagicMock()
        mock_response.text = file_content
        browser._handle_api_request.return_value = mock_response

        return browser

    def test_found_and_parsed(self):
        """Test successful fetch and parse of installer.properties."""
        file_list = [
            {"name": "Launcher.exe", "is_directory": False},
            {"name": "installer.properties", "is_directory": False},
            {"name": "some-installer.jar", "is_directory": False},
        ]
        browser = self._make_mock_browser(file_list, SAMPLE_PROPERTIES_CONTENT)

        result = fetch_installer_properties(browser, "/SoftwarePackage/TEST/v1.0.0")

        assert result["java_version"] == "17.0.16"
        assert result["java_windows"] == "Java/zulujre-windows_x64-17.0.16.zip"
        assert result["java_linux"] == "Java/zulujre-linux_x64-17.0.16.zip"
        assert result["installer_path"] == "GKR-OPOS-ONEX-CLOUD/v5.29.0/onex-launcher-cloud-5.29.0-b11-installer.jar"
        assert result["onex_ui_windows"] == "GKR-OPOS-ONEX-CLOUD/v5.29.0/onex-ui-5.29.0-windows.zip"

    def test_not_found(self):
        """Test returns empty dict when installer.properties is not in listing."""
        file_list = [
            {"name": "Launcher.exe", "is_directory": False},
            {"name": "some-installer.jar", "is_directory": False},
        ]
        browser = self._make_mock_browser(file_list)

        result = fetch_installer_properties(browser, "/SoftwarePackage/TEST/v1.0.0")

        assert result == {}

    def test_directory_with_same_name_ignored(self):
        """Test that a directory named installer.properties is ignored."""
        file_list = [
            {"name": "installer.properties", "is_directory": True},
        ]
        browser = self._make_mock_browser(file_list)

        result = fetch_installer_properties(browser, "/SoftwarePackage/TEST/v1.0.0")

        assert result == {}

    def test_network_error(self):
        """Test graceful handling of network errors during fetch."""
        file_list = [
            {"name": "installer.properties", "is_directory": False},
        ]
        browser = self._make_mock_browser(file_list)
        browser._handle_api_request.side_effect = Exception("Connection timeout")

        result = fetch_installer_properties(browser, "/SoftwarePackage/TEST/v1.0.0")

        assert result == {}

    def test_empty_file(self):
        """Test parsing an empty installer.properties file."""
        file_list = [
            {"name": "installer.properties", "is_directory": False},
        ]
        browser = self._make_mock_browser(file_list, "")

        result = fetch_installer_properties(browser, "/SoftwarePackage/TEST/v1.0.0")

        assert result == {}

    def test_comments_and_blank_lines_skipped(self):
        """Test that comment lines and blank lines are skipped."""
        content = """# This is a comment
! Another comment style

java_version=17.0.16

# Another comment
installer_path=test.jar
"""
        file_list = [
            {"name": "installer.properties", "is_directory": False},
        ]
        browser = self._make_mock_browser(file_list, content)

        result = fetch_installer_properties(browser, "/SoftwarePackage/TEST/v1.0.0")

        assert len(result) == 2
        assert result["java_version"] == "17.0.16"
        assert result["installer_path"] == "test.jar"

    def test_values_with_equals_sign(self):
        """Test that values containing '=' are handled correctly (split on first only)."""
        content = "some_key=value=with=equals"
        file_list = [
            {"name": "installer.properties", "is_directory": False},
        ]
        browser = self._make_mock_browser(file_list, content)

        result = fetch_installer_properties(browser, "/SoftwarePackage/TEST/v1.0.0")

        assert result["some_key"] == "value=with=equals"

    def test_whitespace_trimmed(self):
        """Test that whitespace around keys and values is trimmed."""
        content = "  java_version  =  17.0.16  "
        file_list = [
            {"name": "installer.properties", "is_directory": False},
        ]
        browser = self._make_mock_browser(file_list, content)

        result = fetch_installer_properties(browser, "/SoftwarePackage/TEST/v1.0.0")

        assert result["java_version"] == "17.0.16"

    def test_list_directories_error(self):
        """Test graceful handling when list_directories raises an exception."""
        browser = MagicMock()
        browser.list_directories.side_effect = Exception("API error")

        result = fetch_installer_properties(browser, "/SoftwarePackage/TEST/v1.0.0")

        assert result == {}


class TestBuildInstallerPreferences:
    """Tests for build_installer_preferences()."""

    def _make_sample_properties(self):
        """Return sample parsed properties dict."""
        return {
            "java_version": "17.0.16",
            "java_windows": "Java/zulujre-windows_x64-17.0.16.zip",
            "java_linux": "Java/zulujre-linux_x64-17.0.16.zip",
            "java_mac": "Java/zulujre-macosx_aarch64-17.0.16.tar.gz",
            "onex_ui_windows": "GKR-OPOS-ONEX-CLOUD/v5.29.0/onex-ui-5.29.0-windows.zip",
            "onex_ui_linux": "GKR-OPOS-ONEX-CLOUD/v5.29.0/onex-ui-5.29.0-linux.zip",
            "installer_path": "GKR-OPOS-ONEX-CLOUD/v5.29.0/onex-launcher-cloud-5.29.0-b11-installer.jar",
        }

    def test_windows_platform(self):
        """Test preference resolution for Windows platform."""
        all_props = {"/SoftwarePackage/TEST/v1.0.0": self._make_sample_properties()}
        config = {"platform": "Windows"}

        result = build_installer_preferences(all_props, config)

        assert result["java_file"] == "zulujre-windows_x64-17.0.16.zip"
        assert result["java_path"] == "Java/zulujre-windows_x64-17.0.16.zip"
        assert result["onex_ui_file"] == "onex-ui-5.29.0-windows.zip"
        assert result["source_component"] == "/SoftwarePackage/TEST/v1.0.0"

    def test_linux_platform(self):
        """Test preference resolution for Linux platform."""
        all_props = {"/SoftwarePackage/TEST/v1.0.0": self._make_sample_properties()}
        config = {"platform": "Linux"}

        result = build_installer_preferences(all_props, config)

        assert result["java_file"] == "zulujre-linux_x64-17.0.16.zip"
        assert result["java_path"] == "Java/zulujre-linux_x64-17.0.16.zip"
        assert result["onex_ui_file"] == "onex-ui-5.29.0-linux.zip"

    def test_installer_path_per_component(self):
        """Test that installer_path is stored per version_path."""
        all_props = {
            "/SoftwarePackage/COMP-A/v1.0.0": {
                "installer_path": "COMP-A/v1.0.0/installer-a.jar",
            },
            "/SoftwarePackage/COMP-B/v2.0.0": {
                "installer_path": "COMP-B/v2.0.0/installer-b.jar",
            },
        }
        config = {"platform": "Windows"}

        result = build_installer_preferences(all_props, config)

        assert result["installer_paths"]["/SoftwarePackage/COMP-A/v1.0.0"] == "installer-a.jar"
        assert result["installer_paths"]["/SoftwarePackage/COMP-B/v2.0.0"] == "installer-b.jar"

    def test_first_component_wins_for_java(self):
        """Test that the first component's Java preference takes precedence."""
        all_props = {
            "/SoftwarePackage/FIRST/v1.0.0": {
                "java_windows": "Java/first-java.zip",
            },
            "/SoftwarePackage/SECOND/v2.0.0": {
                "java_windows": "Java/second-java.zip",
            },
        }
        config = {"platform": "Windows"}

        result = build_installer_preferences(all_props, config)

        assert result["java_file"] == "first-java.zip"
        assert result["source_component"] == "/SoftwarePackage/FIRST/v1.0.0"

    def test_empty_properties(self):
        """Test with no properties at all."""
        result = build_installer_preferences({}, {"platform": "Windows"})

        assert result["java_file"] is None
        assert result["java_path"] is None
        assert result["installer_paths"] == {}
        assert result["onex_ui_file"] is None
        assert result["source_component"] is None

    def test_no_java_key_for_platform(self):
        """Test when properties don't have a Java key for the current platform."""
        all_props = {
            "/SoftwarePackage/TEST/v1.0.0": {
                "java_mac": "Java/mac-java.tar.gz",
                "installer_path": "TEST/v1.0.0/test.jar",
            },
        }
        config = {"platform": "Windows"}

        result = build_installer_preferences(all_props, config)

        # java_windows not in props, so java_file should be None
        assert result["java_file"] is None
        # installer_path should still work
        assert result["installer_paths"]["/SoftwarePackage/TEST/v1.0.0"] == "test.jar"

    def test_default_platform_is_windows(self):
        """Test that missing platform config defaults to Windows."""
        all_props = {
            "/SoftwarePackage/TEST/v1.0.0": {
                "java_windows": "Java/win-java.zip",
                "java_linux": "Java/linux-java.zip",
            },
        }
        config = {}  # No platform key

        result = build_installer_preferences(all_props, config)

        assert result["java_file"] == "win-java.zip"

    def test_simple_filename_without_path(self):
        """Test handling of simple filenames without directory path."""
        all_props = {
            "/SoftwarePackage/TEST/v1.0.0": {
                "java_windows": "simple-java.zip",
            },
        }
        config = {"platform": "Windows"}

        result = build_installer_preferences(all_props, config)

        assert result["java_file"] == "simple-java.zip"
        assert result["java_path"] == "simple-java.zip"

    def test_tomcat_preference(self):
        """Test Tomcat preference is extracted from installer.properties."""
        all_props = {
            "/SoftwarePackage/TEST/v1.0.0": {
                "tomcat": "Tomcat/tomcat-cloud-10.1.49.zip",
                "tomcat_version": "10.1.49",
            },
        }
        config = {"platform": "Windows"}

        result = build_installer_preferences(all_props, config)

        assert result["tomcat_file"] == "tomcat-cloud-10.1.49.zip"
        assert result["tomcat_path"] == "Tomcat/tomcat-cloud-10.1.49.zip"

    def test_jaybird_preference(self):
        """Test Jaybird/Firebird driver preference is extracted from installer.properties."""
        all_props = {
            "/SoftwarePackage/TEST/v1.0.0": {
                "firebird_driver_path": "Drivers/jaybird.jar",
            },
        }
        config = {"platform": "Windows"}

        result = build_installer_preferences(all_props, config)

        assert result["jaybird_file"] == "jaybird.jar"
        assert result["jaybird_path"] == "Drivers/jaybird.jar"

    def test_all_platform_deps_from_storehub_properties(self):
        """Test full StoreHub installer.properties with all platform deps."""
        all_props = {
            "/SoftwarePackage/GKR-sh-cloud/v5.29.0": {
                "java_version": "17.0.16",
                "java_windows": "Java/zulujre-windows_x64-17.0.16.zip",
                "java_linux": "Java/zulujre-linux_x64-17.0.16.zip",
                "tomcat_version": "10.1.49",
                "tomcat": "Tomcat/tomcat-cloud-10.1.49.zip",
                "installer_path": "GKR-sh-cloud/v5.29.0/storehub-service-5.29.0-b18-cloud-installer.jar",
                "firebird_driver_path": "Drivers/jaybird.jar",
            },
        }
        config = {"platform": "Windows"}

        result = build_installer_preferences(all_props, config)

        assert result["java_file"] == "zulujre-windows_x64-17.0.16.zip"
        assert result["tomcat_file"] == "tomcat-cloud-10.1.49.zip"
        assert result["jaybird_file"] == "jaybird.jar"
        assert result["installer_paths"]["/SoftwarePackage/GKR-sh-cloud/v5.29.0"] == "storehub-service-5.29.0-b18-cloud-installer.jar"

    def test_first_component_wins_for_tomcat(self):
        """Test that the first component's Tomcat preference takes precedence."""
        all_props = {
            "/SoftwarePackage/FIRST/v1.0.0": {
                "tomcat": "Tomcat/first-tomcat.zip",
            },
            "/SoftwarePackage/SECOND/v2.0.0": {
                "tomcat": "Tomcat/second-tomcat.zip",
            },
        }
        config = {"platform": "Windows"}

        result = build_installer_preferences(all_props, config)

        assert result["tomcat_file"] == "first-tomcat.zip"

    def test_empty_properties_includes_new_keys(self):
        """Test that empty properties includes tomcat and jaybird keys."""
        result = build_installer_preferences({}, {"platform": "Windows"})

        assert result["tomcat_file"] is None
        assert result["tomcat_path"] is None
        assert result["jaybird_file"] is None
        assert result["jaybird_path"] is None
