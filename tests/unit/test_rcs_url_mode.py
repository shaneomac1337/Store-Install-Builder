"""
Tests for the RCS URL mode feature.

Verifies that rcs_url_mode config defaults are correct and that
generate_store_init_script handles hostname/ip modes with proper
protocol and port logic.
"""

import os
import pytest

from gk_install_builder.config import ConfigManager
from gk_install_builder.generators.helper_file_generator import generate_store_init_script
from tests.fixtures.generator_fixtures import create_config

# Minimal template containing only the placeholders under test
MINIMAL_TEMPLATE = "mode=@RCS_URL_MODE@ proto=@RCS_PROTOCOL@ port=@RCS_PORT@ skip=@RCS_SKIP_URL_CONFIG@ ver=@VERSION@"


def _setup_template(tmp_path, platform="Windows"):
    """Create minimal template and directories for a given platform."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    if platform == "Windows":
        filename = "store-initialization.ps1.template"
    else:
        filename = "store-initialization.sh.template"

    (templates_dir / filename).write_text(MINIMAL_TEMPLATE, encoding="utf-8")
    return str(templates_dir), str(output_dir)


def _read_output(output_dir, platform="Windows"):
    """Read the generated store-initialization script."""
    if platform == "Windows":
        filename = "store-initialization.ps1"
    else:
        filename = "store-initialization.sh"
    path = os.path.join(output_dir, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestRcsUrlModeConfigDefault:
    """Test that ConfigManager includes the rcs_url_mode default."""

    def test_default_config_has_rcs_url_mode_hostname(self, monkeypatch, tmp_path):
        """rcs_url_mode should default to 'hostname' in _get_default_config."""
        # Prevent ConfigManager from loading/creating a real config file
        config_file = tmp_path / "gk_install_config.json"
        monkeypatch.setattr(ConfigManager, "__init__", lambda self: None)
        mgr = ConfigManager()
        mgr.config = {}
        mgr.entries = {}
        mgr.save_status_label = None
        mgr.save_timer = None
        mgr.save_in_progress = False
        mgr.config_file = str(config_file)

        defaults = mgr._get_default_config()
        assert "rcs_url_mode" in defaults
        assert defaults["rcs_url_mode"] == "hostname"


class TestRcsUrlModePlaceholderReplacement:
    """Test @RCS_URL_MODE@ placeholder replacement in store-init scripts."""

    def test_hostname_mode_replacement(self, tmp_path):
        """When rcs_url_mode is 'hostname', output should contain 'hostname'."""
        templates_dir, output_dir = _setup_template(tmp_path, "Windows")
        config = create_config(platform="Windows", rcs_url_mode="hostname")
        generate_store_init_script(output_dir, config, templates_dir)

        content = _read_output(output_dir, "Windows")
        assert "mode=hostname" in content
        assert "@RCS_URL_MODE@" not in content

    def test_ip_mode_replacement(self, tmp_path):
        """When rcs_url_mode is 'ip', output should contain 'ip'."""
        templates_dir, output_dir = _setup_template(tmp_path, "Linux")
        config = create_config(platform="Linux", rcs_url_mode="ip")
        generate_store_init_script(output_dir, config, templates_dir)

        content = _read_output(output_dir, "Linux")
        assert "mode=ip" in content
        assert "@RCS_URL_MODE@" not in content


class TestRcsUrlModeProtocolLogic:
    """Test that IP mode forces HTTP and hostname mode allows HTTPS."""

    def test_ip_mode_forces_http_even_when_https_requested(self, tmp_path):
        """IP mode must force protocol=http and port=8180 regardless of rcs_use_https."""
        templates_dir, output_dir = _setup_template(tmp_path, "Windows")
        config = create_config(
            platform="Windows",
            rcs_url_mode="ip",
            rcs_use_https=True,
        )
        generate_store_init_script(output_dir, config, templates_dir)

        content = _read_output(output_dir, "Windows")
        assert "proto=http " in content or "proto=http\n" in content or content.count("proto=http") >= 1
        # Make sure it is NOT https
        assert "proto=https" not in content
        assert "port=8180" in content
        assert "port=8543" not in content

    def test_hostname_mode_with_https(self, tmp_path):
        """Hostname mode with rcs_use_https=True should use https and port 8543."""
        templates_dir, output_dir = _setup_template(tmp_path, "Linux")
        config = create_config(
            platform="Linux",
            rcs_url_mode="hostname",
            rcs_use_https=True,
        )
        generate_store_init_script(output_dir, config, templates_dir)

        content = _read_output(output_dir, "Linux")
        assert "proto=https" in content
        assert "port=8543" in content

    def test_hostname_mode_without_https(self, tmp_path):
        """Hostname mode with rcs_use_https=False should use http and port 8180."""
        templates_dir, output_dir = _setup_template(tmp_path, "Windows")
        config = create_config(
            platform="Windows",
            rcs_url_mode="hostname",
            rcs_use_https=False,
        )
        generate_store_init_script(output_dir, config, templates_dir)

        content = _read_output(output_dir, "Windows")
        assert "proto=http" in content
        assert "proto=https" not in content
        assert "port=8180" in content
