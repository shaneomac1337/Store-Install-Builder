"""Tests for system service installation feature"""
import pytest

try:
    from gk_install_builder.generators.gk_install_generator import build_service_args
except ImportError:
    from generators.gk_install_generator import build_service_args


class TestBuildServiceArgs:
    """Tests for build_service_args function"""

    def test_no_service_enabled_returns_empty(self):
        """When no component has runAsService=1, output is empty"""
        config = {
            "wdm_launcher_settings": {"runAsService": "0"},
            "flow_service_launcher_settings": {},
        }
        result = build_service_args(config, "Windows")
        assert result["ps"] == ""
        assert result["sh"] == ""

    def test_wdm_service_enabled_powershell(self):
        """WDM with service enabled generates correct PS block"""
        config = {
            "wdm_launcher_settings": {
                "runAsService": "1",
                "appServiceName": "Tomcat-wdm",
                "updaterServiceName": "Updater-wdm",
                "runAsServiceStartType": "auto",
            }
        }
        result = build_service_args(config, "Windows")
        assert "if ($ComponentType -eq 'WDM')" in result["ps"]
        assert '"--runAsService", "1"' in result["ps"]
        assert '"--appServiceName", "Tomcat-wdm"' in result["ps"]
        assert '"--updaterServiceName", "Updater-wdm"' in result["ps"]
        assert '"--runAsServiceStartType", "auto"' in result["ps"]

    def test_wdm_service_enabled_bash(self):
        """WDM with service enabled generates correct Bash block (no startType)"""
        config = {
            "wdm_launcher_settings": {
                "runAsService": "1",
                "appServiceName": "Tomcat-wdm",
                "updaterServiceName": "Updater-wdm",
                "runAsServiceStartType": "auto",
            }
        }
        result = build_service_args(config, "Linux")
        assert 'if [ "$COMPONENT_TYPE" = "WDM" ]' in result["sh"]
        assert "--runAsService 1" in result["sh"]
        assert "--appServiceName Tomcat-wdm" in result["sh"]
        assert "--updaterServiceName Updater-wdm" in result["sh"]
        assert "runAsServiceStartType" not in result["sh"]

    def test_multiple_services_enabled(self):
        """Multiple components with service enabled generates blocks for each"""
        config = {
            "wdm_launcher_settings": {
                "runAsService": "1",
                "appServiceName": "Tomcat-wdm",
                "updaterServiceName": "Updater-wdm",
                "runAsServiceStartType": "auto",
            },
            "rcs_service_launcher_settings": {
                "runAsService": "1",
                "appServiceName": "Tomcat-rcs",
                "updaterServiceName": "Updater-rcs",
                "runAsServiceStartType": "manual",
            },
        }
        result = build_service_args(config, "Windows")
        assert "WDM" in result["ps"]
        assert "RCS-SERVICE" in result["ps"]
        assert '"--runAsServiceStartType", "manual"' in result["ps"]

    def test_service_disabled_not_included(self):
        """Component with runAsService=0 is not included"""
        config = {
            "wdm_launcher_settings": {
                "runAsService": "1",
                "appServiceName": "Tomcat-wdm",
                "updaterServiceName": "Updater-wdm",
                "runAsServiceStartType": "auto",
            },
            "flow_service_launcher_settings": {
                "runAsService": "0",
            },
        }
        result = build_service_args(config, "Windows")
        assert "WDM" in result["ps"]
        assert "FLOW-SERVICE" not in result["ps"]

    def test_missing_settings_uses_defaults(self):
        """Missing service name settings fall back to defaults"""
        config = {
            "wdm_launcher_settings": {
                "runAsService": "1",
            }
        }
        result = build_service_args(config, "Windows")
        assert "Tomcat-wdm" in result["ps"]
        assert "Updater-wdm" in result["ps"]

    def test_empty_config_returns_empty(self):
        """Empty config returns empty strings"""
        result = build_service_args({}, "Windows")
        assert result["ps"] == ""
        assert result["sh"] == ""
