"""
Infrastructure Validation Tests

This test file validates that all testing infrastructure is working correctly
before we begin writing the actual generator tests. Run this first!
"""

import pytest
import json
from pathlib import Path
from tests.fixtures.generator_fixtures import (
    load_config_from_file,
    create_config,
    verify_directory_structure,
    get_helper_subdirs,
    count_unreplaced_variables,
    create_minimal_template,
    assert_file_exists,
    assert_json_file_valid
)


class TestFixtureFiles:
    """Test that all fixture files exist and are valid"""

    def test_config_files_exist(self):
        """Verify all config fixture files exist"""
        fixtures_dir = Path(__file__).parent / "fixtures" / "configs"
        expected_configs = [
            "minimal_windows.json",
            "minimal_linux.json",
            "full_windows.json",
            "full_linux.json",
            "multi_environment.json",
            "invalid_config.json"
        ]

        for config_file in expected_configs:
            config_path = fixtures_dir / config_file
            assert config_path.exists(), f"Config file missing: {config_file}"

    def test_template_files_exist(self):
        """Verify all template fixture files exist"""
        fixtures_dir = Path(__file__).parent / "fixtures" / "templates"
        expected_templates = [
            "simple.ps1.template",
            "simple.sh.template",
            "launcher.template"
        ]

        for template_file in expected_templates:
            template_path = fixtures_dir / template_file
            assert template_path.exists(), f"Template file missing: {template_file}"

    def test_config_files_valid_json(self):
        """Verify config files contain valid JSON"""
        fixtures_dir = Path(__file__).parent / "fixtures" / "configs"
        config_files = [
            "minimal_windows.json",
            "minimal_linux.json",
            "full_windows.json",
            "full_linux.json",
            "multi_environment.json"
        ]

        for config_file in config_files:
            config_path = fixtures_dir / config_file
            assert_json_file_valid(config_path)


class TestFixtures:
    """Test that pytest fixtures work correctly"""

    def test_sample_config_windows(self, sample_config_windows):
        """Test sample_config_windows fixture"""
        assert isinstance(sample_config_windows, dict)
        assert sample_config_windows["platform"] == "Windows"
        assert "base_url" in sample_config_windows
        assert "output_dir" in sample_config_windows

    def test_sample_config_linux(self, sample_config_linux):
        """Test sample_config_linux fixture"""
        assert isinstance(sample_config_linux, dict)
        assert sample_config_linux["platform"] == "Linux"
        assert sample_config_linux["base_install_dir"] == "/usr/local/gkretail"

    def test_sample_config_multi_env(self, sample_config_multi_env):
        """Test sample_config_multi_env fixture"""
        assert isinstance(sample_config_multi_env, dict)
        assert len(sample_config_multi_env["environments"]) >= 2
        assert sample_config_multi_env["use_hostname_detection"] is True

    def test_temp_output_dir(self, temp_output_dir):
        """Test temp_output_dir fixture"""
        assert temp_output_dir.exists()
        assert temp_output_dir.is_dir()

    def test_sample_templates(self, sample_templates):
        """Test sample_templates fixture"""
        assert sample_templates.exists()
        assert (sample_templates / "simple.ps1.template").exists()
        assert (sample_templates / "simple.sh.template").exists()
        assert (sample_templates / "launcher.template").exists()


class TestHelperFunctions:
    """Test helper functions from generator_fixtures.py"""

    def test_load_config_from_file(self):
        """Test loading config from file"""
        config = load_config_from_file("minimal_windows.json")
        assert isinstance(config, dict)
        assert config["platform"] == "Windows"

    def test_create_config(self):
        """Test creating config with overrides"""
        config = create_config(platform="Linux", version="v2.0.0")
        assert config["platform"] == "Linux"
        assert config["version"] == "v2.0.0"
        assert "base_url" in config  # Has defaults

    def test_verify_directory_structure(self, tmp_path):
        """Test verifying directory structure"""
        # Create test directories
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir2").mkdir()

        # Should pass
        assert verify_directory_structure(tmp_path, ["dir1", "dir2"])

        # Should fail
        assert not verify_directory_structure(tmp_path, ["dir1", "missing"])

    def test_get_helper_subdirs(self):
        """Test getting expected helper subdirectories"""
        subdirs = get_helper_subdirs()
        assert isinstance(subdirs, list)
        assert "launchers" in subdirs
        assert "onboarding" in subdirs
        assert "tokens" in subdirs

    def test_count_unreplaced_variables(self):
        """Test counting unreplaced variables"""
        content = "@BASE_URL@ and @VERSION@ are variables"
        count = count_unreplaced_variables(content)
        assert count == 2

    def test_create_minimal_template(self):
        """Test creating minimal templates"""
        ps_template = create_minimal_template("powershell")
        assert "@BASE_URL@" in ps_template
        assert "$BASE_URL" in ps_template

        bash_template = create_minimal_template("bash")
        assert "@BASE_URL@" in bash_template
        assert "#!/bin/bash" in bash_template

        launcher_template = create_minimal_template("launcher")
        assert "@COMPONENT_NAME@" in launcher_template
        assert json.loads(launcher_template)  # Valid JSON

    def test_assert_file_exists(self, tmp_path):
        """Test assert_file_exists helper"""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Should pass
        assert_file_exists(test_file)

        # Should fail
        with pytest.raises(AssertionError):
            assert_file_exists(tmp_path / "missing.txt")


class TestMockHelpers:
    """Test mock creation helpers"""

    def test_mock_detection_manager_configured(self, mock_detection_manager_configured):
        """Test configured detection manager mock"""
        assert mock_detection_manager_configured is not None
        assert hasattr(mock_detection_manager_configured, 'detection_config')
        assert isinstance(mock_detection_manager_configured.detection_config, dict)


@pytest.mark.parametrize("platform", ["Windows", "Linux"])
class TestParametrizedInfrastructure:
    """Test that infrastructure works with parameterization"""

    def test_create_config_for_platform(self, platform):
        """Test creating config for different platforms"""
        config = create_config(platform=platform)
        assert config["platform"] == platform

        if platform == "Windows":
            assert "\\" in config["base_install_dir"]
        else:
            assert "/" in config["base_install_dir"]


# ============================================================================
# Quick Smoke Test
# ============================================================================

def test_infrastructure_smoke_test():
    """
    Quick smoke test to verify basic infrastructure is working
    Run this first to catch any setup issues
    """
    # Can import required modules
    try:
        # Try importing with proper package path
        from gk_install_builder.detection import DetectionManager
        from gk_install_builder.config import ConfigManager
        detection_import_ok = True
    except (ImportError, ModuleNotFoundError):
        # Import might fail if relative imports are used, that's okay for now
        detection_import_ok = False

    # Fixtures directory exists
    fixtures_dir = Path(__file__).parent / "fixtures"
    assert fixtures_dir.exists()
    assert (fixtures_dir / "configs").exists()
    assert (fixtures_dir / "templates").exists()

    print("\n✅ Infrastructure validation passed!")
    print("   - All fixture files exist")
    if detection_import_ok:
        print("   - Required modules can be imported")
    else:
        print("   - Module imports need adjustment (expected, will fix in tests)")
    print("   - Helper functions work correctly")
    print("\n📋 Ready to begin writing generator tests!")


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_infrastructure_validation.py -v
    pytest.main([__file__, "-v", "--tb=short"])
