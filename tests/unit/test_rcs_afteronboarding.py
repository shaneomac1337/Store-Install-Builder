"""
Tests for afterOnboardingProperties injection in onboarding scripts.
"""
import os
import pytest
from gk_install_builder.generators.onboarding_generator import generate_onboarding_script
from tests.fixtures.generator_fixtures import create_config


def _setup_templates(tmp_path, platform="Windows"):
    """Copy the real onboarding templates into a temp dir for testing."""
    import shutil
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    src = os.path.join(
        os.path.dirname(__file__), "..", "..",
        "gk_install_builder", "templates"
    )
    for fname in ("onboarding.ps1.template", "onboarding.sh.template"):
        shutil.copy(os.path.join(src, fname), templates_dir / fname)
    return str(templates_dir), str(output_dir)


def _read(output_dir, filename):
    with open(os.path.join(output_dir, filename), "r", encoding="utf-8") as f:
        return f.read()


class TestOnboardingPs1RcsUrlInjection:
    """Onboarding.ps1 must accept -rcsUrl and inject afterOnboardingProperties."""

    def test_ps1_has_rcsurl_param(self, tmp_path):
        templates_dir, output_dir = _setup_templates(tmp_path, "Windows")
        cfg = create_config(platform="Windows")
        generate_onboarding_script(output_dir, cfg, templates_dir)
        content = _read(output_dir, "onboarding.ps1")
        assert '[string]$rcsUrl' in content, (
            "onboarding.ps1 must declare -rcsUrl parameter"
        )

    def test_ps1_injects_afteronboarding_for_non_rcs(self, tmp_path):
        templates_dir, output_dir = _setup_templates(tmp_path, "Windows")
        cfg = create_config(platform="Windows")
        generate_onboarding_script(output_dir, cfg, templates_dir)
        content = _read(output_dir, "onboarding.ps1")
        assert 'afterOnboardingProperties' in content, (
            "onboarding.ps1 must inject afterOnboardingProperties when rcsUrl set"
        )
        assert 'RCS-SERVICE' in content and '-ne "RCS-SERVICE"' in content, (
            "Injection must be gated by ComponentType -ne RCS-SERVICE"
        )
        assert 'rcs.url' in content, (
            "Injection must reference rcs.url key"
        )


class TestOnboardingShRcsUrlInjection:
    """Onboarding.sh must accept --rcsUrl and inject afterOnboardingProperties."""

    def test_sh_has_rcsurl_arg(self, tmp_path):
        templates_dir, output_dir = _setup_templates(tmp_path, "Linux")
        cfg = create_config(platform="Linux")
        generate_onboarding_script(output_dir, cfg, templates_dir)
        content = _read(output_dir, "onboarding.sh")
        assert '--rcsUrl' in content, (
            "onboarding.sh must accept --rcsUrl argument"
        )
        assert 'rcs_url=' in content, (
            "onboarding.sh must initialise rcs_url variable"
        )

    def test_sh_injects_afteronboarding_for_non_rcs(self, tmp_path):
        templates_dir, output_dir = _setup_templates(tmp_path, "Linux")
        cfg = create_config(platform="Linux")
        generate_onboarding_script(output_dir, cfg, templates_dir)
        content = _read(output_dir, "onboarding.sh")
        assert 'afterOnboardingProperties' in content, (
            "onboarding.sh must inject afterOnboardingProperties"
        )
        assert 'RCS-SERVICE' in content and '!= "RCS-SERVICE"' in content, (
            "Injection must be gated by COMPONENT_TYPE != RCS-SERVICE"
        )
        # Both jq path and sed fallback present
        assert 'jq' in content and 'sed' in content, (
            "Both jq and sed fallback paths must be present"
        )

    def test_sh_sed_fallback_anchored_to_last_line(self, tmp_path):
        """Sed fallback must use $ line-address to avoid matching nested braces."""
        templates_dir, output_dir = _setup_templates(tmp_path, "Linux")
        cfg = create_config(platform="Linux")
        generate_onboarding_script(output_dir, cfg, templates_dir)
        content = _read(output_dir, "onboarding.sh")
        assert "sed '$ s/}/" in content or 'sed "$ s/}/' in content, (
            "Sed fallback must be anchored to last line ($ address)"
        )
