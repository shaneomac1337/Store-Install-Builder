"""
Tests for gk_install_builder.generators.template_processor

Tests hostname regex replacement in PowerShell and Bash templates,
including custom patterns, disabled messages, workstation validation
updates, and fallback matching strategies.
"""
import pytest
from gk_install_builder.generators.template_processor import (
    replace_hostname_regex_powershell,
    replace_hostname_regex_bash,
)


# ============================================================================
# PowerShell Hostname Regex Replacement
# ============================================================================

class TestReplaceHostnameRegexPowershell:
    """Tests for replace_hostname_regex_powershell()"""

    @pytest.fixture
    def ps1_template(self):
        """Minimal PowerShell template with hostname detection pattern"""
        return (
            "# Detection\n"
            "if ($hs -match '([^-]+)-(\\d{3})$') {\n"
            "    $storeId = $Matches[1]\n"
            "}\n"
            "$workstationId -match '^\\d{3}$'\n"
        )

    def test_replaces_hostname_regex_with_custom_pattern(self, ps1_template):
        custom = "^POS-(\\d{4})-(\\d{3})$"
        result = replace_hostname_regex_powershell(ps1_template, custom)

        assert f"if ($hs -match '{custom}')" in result
        # Original pattern should be gone
        assert "([^-]+)-(\\d{3})$" not in result

    def test_preserves_surrounding_content(self, ps1_template):
        result = replace_hostname_regex_powershell(ps1_template, "^NEW$")

        assert "# Detection" in result
        assert "$storeId = $Matches[1]" in result

    def test_adds_disabled_message_when_flag_set(self, ps1_template):
        result = replace_hostname_regex_powershell(
            ps1_template, "^TEST$", add_disabled_message=True
        )

        assert "Hostname detection is disabled" in result
        assert "Write-Host" in result
        assert "Yellow" in result
        assert "if ($hs -match '^TEST$') {" in result

    def test_no_disabled_message_by_default(self, ps1_template):
        result = replace_hostname_regex_powershell(ps1_template, "^TEST$")

        assert "Hostname detection is disabled" not in result

    def test_escapes_single_quotes_in_regex(self, ps1_template):
        # PowerShell escapes single quotes by doubling them
        custom = "^POS-'quoted'-(\\d+)$"
        result = replace_hostname_regex_powershell(ps1_template, custom)

        assert "''quoted''" in result

    def test_updates_workstation_validation_pattern(self, ps1_template):
        result = replace_hostname_regex_powershell(ps1_template, "^NEW$")

        # Should replace ^\\d{3}$ with ^\\d+$
        assert "^\\d+$" in result
        assert "^\\d{3}$" not in result

    def test_no_match_returns_content_unchanged(self):
        content = "# No hostname pattern here\n$x = 42\n"
        result = replace_hostname_regex_powershell(content, "^NEW$")

        assert result == content

    def test_empty_template(self):
        result = replace_hostname_regex_powershell("", "^REGEX$")
        assert result == ""

    def test_complex_3group_regex(self, ps1_template):
        custom = "^(\\w+)-POS-(\\d{4})-(\\d{3})$"
        result = replace_hostname_regex_powershell(ps1_template, custom)

        assert f"if ($hs -match '{custom}')" in result

    def test_disabled_message_with_single_quotes_in_regex(self, ps1_template):
        custom = "^POS-'test'$"
        result = replace_hostname_regex_powershell(
            ps1_template, custom, add_disabled_message=True
        )

        assert "Hostname detection is disabled" in result
        assert "''test''" in result


# ============================================================================
# Bash Hostname Regex Replacement
# ============================================================================

class TestReplaceHostnameRegexBash:
    """Tests for replace_hostname_regex_bash()"""

    @pytest.fixture
    def sh_template(self):
        """Minimal Bash template with the exact target line"""
        return (
            '#!/bin/bash\n'
            '    if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]]; then\n'
            '        storeId="${BASH_REMATCH[1]}"\n'
            '    fi\n'
            '    [[ "$workstationId" =~ ^[0-9]{3}$ ]]\n'
        )

    def test_replaces_exact_target_line(self, sh_template):
        custom = "^POS-([0-9]{4})-([0-9]{3})$"
        result = replace_hostname_regex_bash(sh_template, custom)

        assert f'if [[ "$hs" =~ {custom} ]]; then' in result
        assert '([^-]+)-([0-9]+)$' not in result

    def test_preserves_surrounding_content(self, sh_template):
        result = replace_hostname_regex_bash(sh_template, "^NEW$")

        assert "#!/bin/bash" in result
        assert 'storeId="${BASH_REMATCH[1]}"' in result

    def test_adds_disabled_message_when_flag_set(self, sh_template):
        result = replace_hostname_regex_bash(
            sh_template, "^TEST$", add_disabled_message=True
        )

        assert "Hostname detection is disabled" in result
        assert 'echo "Hostname detection is disabled' in result
        assert 'if [[ "$hs" =~ ^TEST$ ]]; then' in result

    def test_no_disabled_message_by_default(self, sh_template):
        result = replace_hostname_regex_bash(sh_template, "^TEST$")

        assert "Hostname detection is disabled" not in result

    def test_updates_workstation_validation_pattern(self, sh_template):
        result = replace_hostname_regex_bash(sh_template, "^NEW$")

        assert '^[0-9]+$' in result
        assert '^[0-9]{3}$' not in result

    def test_workstation_pattern_unchanged_if_not_present(self):
        content = '    if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]]; then\n'
        result = replace_hostname_regex_bash(content, "^NEW$")

        # No workstation pattern to update, should not error
        assert 'if [[ "$hs" =~ ^NEW$ ]]; then' in result

    # ---- Fallback matching strategies ----

    def test_fallback_no_indent(self):
        """Matches variant with no leading spaces"""
        content = 'if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]]; then\necho done\n'
        result = replace_hostname_regex_bash(content, "^CUSTOM$")

        assert 'if [[ "$hs" =~ ^CUSTOM$ ]]; then' in result

    def test_fallback_two_space_indent(self):
        """Matches variant with 2-space indent"""
        content = '  if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]]; then\n'
        result = replace_hostname_regex_bash(content, "^CUSTOM$")

        assert '  if [[ "$hs" =~ ^CUSTOM$ ]]; then' in result

    def test_fallback_six_space_indent(self):
        """Matches variant with 6-space indent"""
        content = '      if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]]; then\n'
        result = replace_hostname_regex_bash(content, "^CUSTOM$")

        assert '      if [[ "$hs" =~ ^CUSTOM$ ]]; then' in result

    def test_fallback_no_space_before_then(self):
        """Matches variant without space before 'then' (;then)"""
        content = '    if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]];then\n'
        result = replace_hostname_regex_bash(content, "^CUSTOM$")

        assert 'if [[ "$hs" =~ ^CUSTOM$ ]]; then' in result

    def test_fallback_bare_regex_pattern(self):
        """Falls back to replacing just the regex pattern itself"""
        content = 'some_other_construct "([^-]+)-([0-9]+)$" more\n'
        result = replace_hostname_regex_bash(content, "^FALLBACK$")

        assert "^FALLBACK$" in result
        assert "([^-]+)-([0-9]+)$" not in result

    def test_fallback_bare_regex_also_updates_workstation(self):
        """Bare regex fallback also updates workstation validation"""
        content = 'stuff ([^-]+)-([0-9]+)$ more\n^[0-9]{3}$ validation\n'
        result = replace_hostname_regex_bash(content, "^NEW$")

        assert "^[0-9]+$" in result
        assert "^[0-9]{3}$" not in result

    def test_no_match_returns_original(self):
        """When no patterns match at all, returns original content"""
        content = "#!/bin/bash\necho hello\n"
        result = replace_hostname_regex_bash(content, "^NEW$")

        assert result == content

    def test_empty_template(self):
        result = replace_hostname_regex_bash("", "^REGEX$")
        assert result == ""

    def test_complex_3group_regex(self, sh_template):
        custom = "^([A-Z]+)-([0-9]{4})-([0-9]{3})$"
        result = replace_hostname_regex_bash(sh_template, custom)

        assert f'if [[ "$hs" =~ {custom} ]]; then' in result

    @pytest.mark.parametrize("indent", ["", "  ", "    ", "      "])
    def test_fallback_variants_preserve_indentation(self, indent):
        content = f'{indent}if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]]; then\n'
        result = replace_hostname_regex_bash(content, "^PAT$")

        # Result should have the replacement with proper indent
        assert 'if [[ "$hs" =~ ^PAT$ ]]; then' in result


# ============================================================================
# Cross-function consistency
# ============================================================================

class TestCrossPlatformConsistency:
    """Verify that PS1 and SH functions behave consistently for the same inputs"""

    @pytest.fixture
    def ps1_template(self):
        return (
            "if ($hs -match '([^-]+)-(\\d{3})$') {\n"
            "$workstationId -match '^\\d{3}$'\n"
        )

    @pytest.fixture
    def sh_template(self):
        return (
            '    if [[ "$hs" =~ ([^-]+)-([0-9]+)$ ]]; then\n'
            '    [[ "$workstationId" =~ ^[0-9]{3}$ ]]\n'
        )

    def test_both_replace_custom_regex(self, ps1_template, sh_template):
        custom = "^STORE-(\\d{4})-(\\d{3})$"

        ps1_result = replace_hostname_regex_powershell(ps1_template, custom)
        sh_result = replace_hostname_regex_bash(sh_template, custom)

        assert custom in ps1_result
        assert custom in sh_result

    def test_both_add_disabled_message(self, ps1_template, sh_template):
        custom = "^TEST$"

        ps1_result = replace_hostname_regex_powershell(
            ps1_template, custom, add_disabled_message=True
        )
        sh_result = replace_hostname_regex_bash(
            sh_template, custom, add_disabled_message=True
        )

        assert "Hostname detection is disabled" in ps1_result
        assert "Hostname detection is disabled" in sh_result

    def test_both_update_workstation_validation(self, ps1_template, sh_template):
        custom = "^NEW$"

        ps1_result = replace_hostname_regex_powershell(ps1_template, custom)
        sh_result = replace_hostname_regex_bash(sh_template, custom)

        # Both should relax workstation validation from {3} to +
        assert "^\\d{3}$" not in ps1_result
        assert "^[0-9]{3}$" not in sh_result
