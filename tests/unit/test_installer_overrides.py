"""
Tests for installer override XML generation
"""

import os
import pytest
import shutil
from pathlib import Path


class TestGenerateOverrideFiles:
    """Tests for generate_override_files function"""

    def _get_templates_dir(self):
        """Get the real templates directory"""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "gk_install_builder", "templates"
        )

    def test_generate_override_files_creates_all_files(self, tmp_path):
        """When enabled, all 7 override XML files should be created"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {"installer_overrides_enabled": True}
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        overrides_dir = helper_dir / "overrides"
        assert overrides_dir.exists()

        expected_files = [
            "installer_overrides.pos.xml",
            "installer_overrides.onex-pos.xml",
            "installer_overrides.wdm.xml",
            "installer_overrides.flow-service.xml",
            "installer_overrides.lpa-service.xml",
            "installer_overrides.storehub-service.xml",
            "installer_overrides.rcs-service.xml",
        ]
        for filename in expected_files:
            assert (overrides_dir / filename).exists(), f"Missing override file: {filename}"

    def test_generate_override_files_disabled(self, tmp_path):
        """When disabled, no override files should be created"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {"installer_overrides_enabled": False}
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        overrides_dir = helper_dir / "overrides"
        assert not overrides_dir.exists()

    def test_override_file_placeholders_substituted(self, tmp_path):
        """Output files should have placeholders replaced with config values"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {
            "installer_overrides_enabled": True,
            "installer_overrides_properties": {
                "check-alive": True,
                "start-application": False,
            },
        }
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        # Check POS override has substituted values (not raw placeholders)
        output_path = helper_dir / "overrides" / "installer_overrides.pos.xml"
        content = output_path.read_text()

        assert "@OVERRIDE_CHECK_ALIVE@" not in content
        assert "@OVERRIDE_START_APPLICATION@" not in content
        assert 'name="override.check-alive" value="true"' in content
        assert 'name="override.start-application" value="false"' in content
        # start-updater is always hardcoded false (not configurable)
        assert 'name="override.start-updater" value="false"' in content

    def test_override_file_contains_check_alive(self, tmp_path):
        """All override files should contain check-alive set to true by default"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {
            "installer_overrides_enabled": True,
            "installer_overrides_properties": {
                "check-alive": True,
                "start-application": False,
            },
        }
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        overrides_dir = helper_dir / "overrides"
        for xml_file in overrides_dir.iterdir():
            content = xml_file.read_text()
            assert 'override.check-alive' in content, f"{xml_file.name} missing check-alive property"
            assert 'name="override.check-alive" value="true"' in content, f"{xml_file.name} missing check-alive=true"

    def test_shared_services_template_reused(self, tmp_path):
        """Flow, LPA, and RCS should all use the same Services template"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {"installer_overrides_enabled": True}
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        overrides_dir = helper_dir / "overrides"
        flow_content = (overrides_dir / "installer_overrides.flow-service.xml").read_text()
        lpa_content = (overrides_dir / "installer_overrides.lpa-service.xml").read_text()
        rcs_content = (overrides_dir / "installer_overrides.rcs-service.xml").read_text()

        assert flow_content == lpa_content
        assert lpa_content == rcs_content

    def test_override_missing_template_graceful(self, tmp_path):
        """Missing template should not crash, just warn"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {"installer_overrides_enabled": True}

        # Use an empty templates dir with no overrides subfolder
        empty_templates = tmp_path / "empty_templates"
        empty_templates.mkdir()

        # Should not raise
        generate_override_files(str(helper_dir), config, str(empty_templates))

        # Overrides dir should be created but empty
        overrides_dir = helper_dir / "overrides"
        assert overrides_dir.exists()
        assert len(list(overrides_dir.iterdir())) == 0

    def test_config_default_includes_overrides_key(self):
        """Default config should include installer_overrides_enabled"""
        from gk_install_builder.config import ConfigManager

        cm = ConfigManager()
        default = cm._get_default_config()
        assert "installer_overrides_enabled" in default
        assert default["installer_overrides_enabled"] is True


class TestOverrideProperties:
    """Tests for configurable override property substitution"""

    def _get_templates_dir(self):
        """Get the real templates directory"""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "gk_install_builder", "templates"
        )

    def test_override_properties_both_true(self, tmp_path):
        """When both properties are True, both should be 'true' in output"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {
            "installer_overrides_enabled": True,
            "installer_overrides_properties": {
                "check-alive": True,
                "start-application": True,
            },
        }
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        content = (helper_dir / "overrides" / "installer_overrides.pos.xml").read_text()
        assert 'name="override.check-alive" value="true"' in content
        assert 'name="override.start-application" value="true"' in content

    def test_override_properties_both_false(self, tmp_path):
        """When both properties are False, both should be 'false' in output"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {
            "installer_overrides_enabled": True,
            "installer_overrides_properties": {
                "check-alive": False,
                "start-application": False,
            },
        }
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        content = (helper_dir / "overrides" / "installer_overrides.pos.xml").read_text()
        assert 'name="override.check-alive" value="false"' in content
        assert 'name="override.start-application" value="false"' in content

    def test_override_start_application_true(self, tmp_path):
        """Verify start-application=true when configured, check-alive at default"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {
            "installer_overrides_enabled": True,
            "installer_overrides_properties": {
                "check-alive": True,
                "start-application": True,
            },
        }
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        content = (helper_dir / "overrides" / "installer_overrides.wdm.xml").read_text()
        assert 'name="override.check-alive" value="true"' in content
        assert 'name="override.start-application" value="true"' in content

    def test_start_updater_always_hardcoded_false(self, tmp_path):
        """start-updater should always be hardcoded to false (not configurable)"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {
            "installer_overrides_enabled": True,
            "installer_overrides_properties": {
                "check-alive": True,
                "start-application": True,
            },
        }
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        # All non-addon templates should have start-updater hardcoded to false
        overrides_dir = helper_dir / "overrides"
        for xml_file in overrides_dir.iterdir():
            content = xml_file.read_text()
            if 'override.start-updater' in content:
                assert 'name="override.start-updater" value="false"' in content, \
                    f"{xml_file.name} has start-updater not set to false"

    def test_addon_has_no_start_updater(self, tmp_path):
        """Addon template should not have start-updater property"""
        templates_dir = self._get_templates_dir()
        addon_template = Path(templates_dir) / "overrides" / "installer_overrides_Addon.xml"
        addon_content = addon_template.read_text()
        assert 'override.start-updater' not in addon_content
        assert 'override.start-application' in addon_content
        assert 'override.check-alive' in addon_content

    def test_override_default_properties_in_config(self):
        """Default config should include installer_overrides_properties with correct defaults"""
        from gk_install_builder.config import ConfigManager

        cm = ConfigManager()
        default = cm._get_default_config()
        assert "installer_overrides_properties" in default
        props = default["installer_overrides_properties"]
        assert props["check-alive"] is True
        assert props["start-application"] is False
        assert "start-updater" not in props

    def test_override_properties_missing_uses_defaults(self, tmp_path):
        """When installer_overrides_properties is missing from config, defaults are used"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {"installer_overrides_enabled": True}
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        content = (helper_dir / "overrides" / "installer_overrides.pos.xml").read_text()
        # Defaults: check-alive=true, start-application=false
        assert 'name="override.check-alive" value="true"' in content
        assert 'name="override.start-application" value="false"' in content

    def test_override_properties_applied_to_all_components(self, tmp_path):
        """Override properties should be applied consistently across all component files"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {
            "installer_overrides_enabled": True,
            "installer_overrides_properties": {
                "check-alive": False,
                "start-application": True,
            },
        }
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        overrides_dir = helper_dir / "overrides"
        for xml_file in overrides_dir.iterdir():
            content = xml_file.read_text()
            assert 'name="override.check-alive" value="false"' in content, \
                f"{xml_file.name} has wrong check-alive value"
            assert 'name="override.start-application" value="true"' in content, \
                f"{xml_file.name} has wrong start-application value"
            # No leftover placeholders
            assert "@OVERRIDE_" not in content, \
                f"{xml_file.name} has unreplaced placeholders"


class TestPerComponentOverrides:
    """Tests for per-component override selection"""

    def _get_templates_dir(self):
        """Get the real templates directory"""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "gk_install_builder", "templates"
        )

    def test_only_selected_components_generated(self, tmp_path):
        """Only components enabled in installer_overrides_components should be generated"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {
            "installer_overrides_enabled": True,
            "installer_overrides_components": {
                "POS": True,
                "ONEX-POS": False,
                "WDM": True,
                "FLOW-SERVICE": False,
                "LPA-SERVICE": False,
                "STOREHUB-SERVICE": False,
                "RCS-SERVICE": False,
            }
        }
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        overrides_dir = helper_dir / "overrides"
        generated = {f.name for f in overrides_dir.iterdir()}

        assert "installer_overrides.pos.xml" in generated
        assert "installer_overrides.wdm.xml" in generated
        assert len(generated) == 2

    def test_all_components_disabled_skips_generation(self, tmp_path):
        """If all components are disabled, no files should be generated"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {
            "installer_overrides_enabled": True,
            "installer_overrides_components": {
                "POS": False,
                "ONEX-POS": False,
                "WDM": False,
                "FLOW-SERVICE": False,
                "LPA-SERVICE": False,
                "STOREHUB-SERVICE": False,
                "RCS-SERVICE": False,
            }
        }
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        overrides_dir = helper_dir / "overrides"
        assert not overrides_dir.exists()

    def test_missing_components_config_defaults_to_all_enabled(self, tmp_path):
        """If installer_overrides_components is missing, all components default to enabled"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {"installer_overrides_enabled": True}
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        overrides_dir = helper_dir / "overrides"
        assert len(list(overrides_dir.iterdir())) == 7

    def test_single_component_enabled(self, tmp_path):
        """Enabling only one component should produce exactly one file"""
        from gk_install_builder.generators.helper_file_generator import generate_override_files

        helper_dir = tmp_path / "helper"
        helper_dir.mkdir()
        config = {
            "installer_overrides_enabled": True,
            "installer_overrides_components": {
                "POS": False,
                "ONEX-POS": False,
                "WDM": False,
                "FLOW-SERVICE": False,
                "LPA-SERVICE": False,
                "STOREHUB-SERVICE": True,
                "RCS-SERVICE": False,
            }
        }
        templates_dir = self._get_templates_dir()

        generate_override_files(str(helper_dir), config, templates_dir)

        overrides_dir = helper_dir / "overrides"
        generated = list(overrides_dir.iterdir())
        assert len(generated) == 1
        assert generated[0].name == "installer_overrides.storehub-service.xml"

    def test_config_default_includes_components_dict(self):
        """Default config should include installer_overrides_components with all True"""
        from gk_install_builder.config import ConfigManager

        cm = ConfigManager()
        default = cm._get_default_config()
        assert "installer_overrides_components" in default
        components = default["installer_overrides_components"]
        assert len(components) == 7
        assert all(v is True for v in components.values())


class TestOverrideTemplateMap:
    """Tests for OVERRIDE_TEMPLATE_MAP configuration"""

    def test_override_template_map_has_all_entries(self):
        """OVERRIDE_TEMPLATE_MAP should have 7 entries"""
        from gk_install_builder.gen_config.generator_config import OVERRIDE_TEMPLATE_MAP
        assert len(OVERRIDE_TEMPLATE_MAP) == 7

    def test_override_component_files_has_all_entries(self):
        """OVERRIDE_COMPONENT_FILES should have 7 entries"""
        from gk_install_builder.gen_config.generator_config import OVERRIDE_COMPONENT_FILES
        assert len(OVERRIDE_COMPONENT_FILES) == 7

    def test_component_files_match_template_map_keys(self):
        """All OVERRIDE_COMPONENT_FILES values should be keys in OVERRIDE_TEMPLATE_MAP"""
        from gk_install_builder.gen_config.generator_config import OVERRIDE_TEMPLATE_MAP, OVERRIDE_COMPONENT_FILES
        for comp, filename in OVERRIDE_COMPONENT_FILES.items():
            assert filename in OVERRIDE_TEMPLATE_MAP, f"{filename} (for {comp}) not in OVERRIDE_TEMPLATE_MAP"

    def test_helper_structure_has_overrides(self):
        """HELPER_STRUCTURE should include overrides directory"""
        from gk_install_builder.gen_config.generator_config import HELPER_STRUCTURE
        assert "overrides" in HELPER_STRUCTURE
        assert len(HELPER_STRUCTURE["overrides"]) == 7

    def test_all_template_sources_exist(self):
        """All template source files referenced in OVERRIDE_TEMPLATE_MAP should exist"""
        from gk_install_builder.gen_config.generator_config import OVERRIDE_TEMPLATE_MAP

        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "gk_install_builder", "templates", "overrides"
        )

        for output_name, template_name in OVERRIDE_TEMPLATE_MAP.items():
            template_path = os.path.join(templates_dir, template_name)
            assert os.path.exists(template_path), f"Template missing: {template_name} (for {output_name})"
