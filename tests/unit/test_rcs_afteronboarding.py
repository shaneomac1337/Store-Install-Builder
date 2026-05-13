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
        """Sed fallback must use $ line-address and a delimiter safe for URLs."""
        templates_dir, output_dir = _setup_templates(tmp_path, "Linux")
        cfg = create_config(platform="Linux")
        generate_onboarding_script(output_dir, cfg, templates_dir)
        content = _read(output_dir, "onboarding.sh")
        # Anchored to last line ($ address) AND uses | delimiter (RCS URLs contain /)
        assert "sed '$ s|}|" in content, (
            "Sed fallback must be anchored to last line ($ address) and use | delimiter"
        )

    def test_sh_sed_fallback_does_not_use_slash_delimiter(self, tmp_path):
        """Regression: sed must not use / as the delimiter (RCS URLs contain /)."""
        templates_dir, output_dir = _setup_templates(tmp_path, "Linux")
        cfg = create_config(platform="Linux")
        generate_onboarding_script(output_dir, cfg, templates_dir)
        content = _read(output_dir, "onboarding.sh")
        assert "sed '$ s/}/" not in content, (
            "Sed fallback must not use / delimiter (breaks on URLs containing /)"
        )


class TestGKInstallPs1RcsUrlPreOnboarding:
    """GKInstall.ps1 must resolve rcsUrl BEFORE onboarding.ps1 is invoked."""

    def _generate_ps1(self, tmp_path):
        """Generate GKInstall.ps1 via the real generator and return its content."""
        from gk_install_builder.generator import ProjectGenerator
        from tests.unit.test_generator_integration import (
            TestCompleteProjectGeneration,
        )
        output_dir = tmp_path / "rcs_pre_onboarding"
        output_dir.mkdir()
        cfg = create_config(
            platform="Windows",
            output_dir=str(output_dir),
            include_pos=True,
            pos_version="v1.0.0",
        )
        gen = ProjectGenerator()
        TestCompleteProjectGeneration._configure_detection_manager(gen)
        gen.generate(cfg)
        ps1_path = os.path.join(str(output_dir), "GKInstall.ps1")
        with open(ps1_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_onboarding_call_passes_rcsurl(self, tmp_path):
        content = self._generate_ps1(tmp_path)
        # The .\onboarding.ps1 invocation must include -rcsUrl $rcsUrl
        assert '.\\onboarding.ps1' in content
        assert '-rcsUrl $rcsUrl' in content, (
            "GKInstall.ps1 must pass -rcsUrl when calling onboarding.ps1"
        )

    def test_autodetect_runs_before_onboarding_call(self, tmp_path):
        content = self._generate_ps1(tmp_path)
        autodetect_marker = "Autodetecting RCS URL from config-service"
        onboarding_marker = ".\\onboarding.ps1"
        a_idx = content.find(autodetect_marker)
        o_idx = content.find(onboarding_marker)
        assert a_idx >= 0, "Autodetect block not found"
        assert o_idx >= 0, "Onboarding invocation not found"
        assert a_idx < o_idx, (
            f"Autodetect block (idx={a_idx}) must appear BEFORE onboarding call (idx={o_idx})"
        )

    def test_autodetect_block_not_duplicated(self, tmp_path):
        content = self._generate_ps1(tmp_path)
        marker = "Autodetecting RCS URL from config-service"
        assert content.count(marker) == 1, (
            f"Autodetect block must appear exactly once, found {content.count(marker)}"
        )


class TestGKInstallShRcsUrlPreOnboarding:
    """GKInstall.sh must resolve rcs_url BEFORE onboarding.sh is invoked."""

    def _generate_sh(self, tmp_path):
        """Generate GKInstall.sh via the real generator and return its content."""
        from gk_install_builder.generator import ProjectGenerator
        from tests.unit.test_generator_integration import (
            TestCompleteProjectGeneration,
        )
        output_dir = tmp_path / "rcs_pre_onboarding_sh"
        output_dir.mkdir()
        cfg = create_config(
            platform="Linux",
            output_dir=str(output_dir),
            include_pos=True,
            pos_version="v1.0.0",
        )
        gen = ProjectGenerator()
        TestCompleteProjectGeneration._configure_detection_manager(gen)
        gen.generate(cfg)
        sh_path = os.path.join(str(output_dir), "GKInstall.sh")
        with open(sh_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_onboarding_call_passes_rcsurl(self, tmp_path):
        content = self._generate_sh(tmp_path)
        assert './onboarding.sh' in content
        assert '--rcsUrl "$rcs_url"' in content, (
            "GKInstall.sh must pass --rcsUrl when calling onboarding.sh"
        )

    def test_autodetect_runs_before_onboarding_call(self, tmp_path):
        content = self._generate_sh(tmp_path)
        autodetect_marker = "Autodetecting RCS URL from config-service"
        onboarding_marker = "./onboarding.sh"
        a_idx = content.find(autodetect_marker)
        o_idx = content.find(onboarding_marker)
        assert a_idx >= 0 and o_idx >= 0
        assert a_idx < o_idx, (
            f"Autodetect block (idx={a_idx}) must appear BEFORE onboarding call (idx={o_idx})"
        )

    def test_autodetect_block_not_duplicated(self, tmp_path):
        content = self._generate_sh(tmp_path)
        marker = "Autodetecting RCS URL from config-service"
        assert content.count(marker) == 1


class TestRcsUrlEndToEndFlow:
    """Verify the full rcsUrl flow end-to-end across generated scripts."""

    def test_ps1_full_flow_consistent(self, tmp_path):
        """When rcsUrl is set, the generated PS1 chain wires it correctly."""
        from gk_install_builder.generator import ProjectGenerator
        from tests.unit.test_generator_integration import (
            TestCompleteProjectGeneration,
        )
        output_dir = tmp_path / "rcs_e2e_ps1"
        output_dir.mkdir()
        cfg = create_config(
            platform="Windows",
            output_dir=str(output_dir),
            include_pos=True,
            pos_version="v1.0.0",
        )
        gen = ProjectGenerator()
        TestCompleteProjectGeneration._configure_detection_manager(gen)
        gen.generate(cfg)

        gk_path = os.path.join(str(output_dir), "GKInstall.ps1")
        ob_path = os.path.join(str(output_dir), "onboarding.ps1")
        with open(gk_path, "r", encoding="utf-8") as f:
            gk = f.read()
        with open(ob_path, "r", encoding="utf-8") as f:
            ob = f.read()

        # GKInstall passes rcsUrl
        assert '-rcsUrl $rcsUrl' in gk
        # Autodetect lives in GKInstall before onboarding call
        assert gk.find("Autodetecting RCS URL") < gk.find(".\\onboarding.ps1")
        # Onboarding accepts param + injects
        assert '[string]$rcsUrl' in ob
        assert 'afterOnboardingProperties' in ob
        assert '-ne "RCS-SERVICE"' in ob
        # Legacy installationtoken.txt append still present
        assert 'rcs.url=$rcsUrl' in gk or '`nrcs.url=$rcsUrl' in gk

    def test_sh_full_flow_consistent(self, tmp_path):
        """When rcs_url is set, the generated SH chain wires it correctly."""
        from gk_install_builder.generator import ProjectGenerator
        from tests.unit.test_generator_integration import (
            TestCompleteProjectGeneration,
        )
        output_dir = tmp_path / "rcs_e2e_sh"
        output_dir.mkdir()
        cfg = create_config(
            platform="Linux",
            output_dir=str(output_dir),
            include_pos=True,
            pos_version="v1.0.0",
        )
        gen = ProjectGenerator()
        TestCompleteProjectGeneration._configure_detection_manager(gen)
        gen.generate(cfg)

        gk_path = os.path.join(str(output_dir), "GKInstall.sh")
        ob_path = os.path.join(str(output_dir), "onboarding.sh")
        with open(gk_path, "r", encoding="utf-8") as f:
            gk = f.read()
        with open(ob_path, "r", encoding="utf-8") as f:
            ob = f.read()

        assert '--rcsUrl "$rcs_url"' in gk
        assert gk.find("Autodetecting RCS URL") < gk.find("./onboarding.sh")
        assert '--rcsUrl' in ob
        assert 'afterOnboardingProperties' in ob
        assert '!= "RCS-SERVICE"' in ob
        # Legacy installationtoken.txt append still present
        assert 'rcs.url=$rcs_url' in gk
