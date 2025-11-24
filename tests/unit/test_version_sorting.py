"""
Unit tests for version sorting utilities.

Tests robust version comparison, sorting, and edge case handling.
"""

import pytest
from gk_install_builder.utils.version_sorting import (
    normalize_version_string,
    parse_version_safe,
    sort_versions,
    get_latest_version,
    compare_versions,
    is_prerelease
)


class TestNormalizeVersionString:
    """Test version string normalization."""

    def test_remove_v_prefix(self):
        """Test removal of 'v' prefix."""
        assert normalize_version_string("v5.27.0") == "5.27.0"
        assert normalize_version_string("V5.27.0") == "5.27.0"

    def test_no_prefix(self):
        """Test version without prefix."""
        assert normalize_version_string("5.27.0") == "5.27.0"

    def test_incomplete_version(self):
        """Test incomplete versions get patch added."""
        assert normalize_version_string("5.27") == "5.27.0"
        assert normalize_version_string("v5.27") == "5.27.0"

    def test_incomplete_version_with_prerelease(self):
        """Test incomplete versions with pre-release tags."""
        # Should add .0 before pre-release tag
        result = normalize_version_string("v5.27-RC1")
        assert result.startswith("5.27.0")
        assert "rc1" in result.lower()

    def test_prerelease_normalization(self):
        """Test pre-release tag normalization."""
        assert "rc1" in normalize_version_string("v5.27.0-RC1").lower()
        assert "rc2" in normalize_version_string("5.27.0-rc2").lower()
        assert "b" in normalize_version_string("v5.27.0-beta")
        assert "a" in normalize_version_string("v5.27.0-alpha")
        assert "dev" in normalize_version_string("v5.27.0-SNAPSHOT")

    def test_build_metadata_preserved(self):
        """Test build metadata is preserved."""
        result = normalize_version_string("v5.27.0+build123")
        assert "5.27.0" in result
        assert "build123" in result

    def test_whitespace_handling(self):
        """Test whitespace is stripped."""
        assert normalize_version_string("  v5.27.0  ") == "5.27.0"
        assert normalize_version_string("\tv5.27.0\n") == "5.27.0"


class TestParseVersionSafe:
    """Test safe version parsing."""

    def test_valid_version(self):
        """Test parsing valid version."""
        version, original = parse_version_safe("v5.27.0")
        assert version is not None
        assert original == "v5.27.0"
        assert version.major == 5
        assert version.minor == 27
        assert version.micro == 0

    def test_invalid_version(self):
        """Test parsing invalid version returns None."""
        version, original = parse_version_safe("invalid")
        assert version is None
        assert original == "invalid"

    def test_original_preserved(self):
        """Test original format is preserved."""
        _, original = parse_version_safe("v5.27.0")
        assert original == "v5.27.0"

        _, original = parse_version_safe("5.27.0")
        assert original == "5.27.0"

    def test_prerelease_version(self):
        """Test parsing pre-release versions."""
        version, _ = parse_version_safe("v5.27.0-RC1")
        assert version is not None
        assert version.is_prerelease

    def test_edge_cases(self):
        """Test edge cases."""
        # Empty string
        version, _ = parse_version_safe("")
        assert version is None

        # Just 'v'
        version, _ = parse_version_safe("v")
        assert version is None

        # Malformed
        version, _ = parse_version_safe("v5.x.y")
        assert version is None


class TestSortVersions:
    """Test version sorting functionality."""

    def test_sort_descending(self):
        """Test sorting newest to oldest (default)."""
        versions = ["v5.26.0", "v5.27.0", "v5.25.0"]
        sorted_versions = sort_versions(versions)
        assert sorted_versions == ["v5.27.0", "v5.26.0", "v5.25.0"]

    def test_sort_ascending(self):
        """Test sorting oldest to newest."""
        versions = ["v5.26.0", "v5.27.0", "v5.25.0"]
        sorted_versions = sort_versions(versions, descending=False)
        assert sorted_versions == ["v5.25.0", "v5.26.0", "v5.27.0"]

    def test_prerelease_older_than_release(self):
        """Test pre-release versions sort before release versions."""
        versions = ["v5.27.0", "v5.27.0-RC1", "v5.27.0-beta"]
        sorted_versions = sort_versions(versions)
        # Release should be first, then RC, then beta
        assert sorted_versions[0] == "v5.27.0"
        assert "RC1" in sorted_versions[1] or "beta" in sorted_versions[1]

    def test_multiple_prereleases(self):
        """Test sorting multiple pre-release versions."""
        versions = ["v5.27.0-RC1", "v5.27.0-RC2", "v5.27.0"]
        sorted_versions = sort_versions(versions)
        assert sorted_versions[0] == "v5.27.0"
        # RC2 should be newer than RC1
        rc2_index = next(i for i, v in enumerate(sorted_versions) if "RC2" in v)
        rc1_index = next(i for i, v in enumerate(sorted_versions) if "RC1" in v)
        assert rc2_index < rc1_index

    def test_mixed_formats(self):
        """Test sorting mixed formats (with/without 'v')."""
        versions = ["v5.27.0", "5.26.0", "v5.26.1"]
        sorted_versions = sort_versions(versions)
        assert sorted_versions == ["v5.27.0", "v5.26.1", "5.26.0"]

    def test_invalid_versions_at_end(self):
        """Test invalid versions placed at end."""
        versions = ["v5.27.0", "invalid", "v5.26.0", "bad_version"]
        sorted_versions = sort_versions(versions)
        # Valid versions first
        assert sorted_versions[0] == "v5.27.0"
        assert sorted_versions[1] == "v5.26.0"
        # Invalid versions at end
        assert "invalid" in sorted_versions[2:]
        assert "bad_version" in sorted_versions[2:]

    def test_empty_list(self):
        """Test empty list handling."""
        assert sort_versions([]) == []

    def test_single_version(self):
        """Test single version."""
        assert sort_versions(["v5.27.0"]) == ["v5.27.0"]

    def test_snapshot_versions(self):
        """Test SNAPSHOT versions sort as dev releases."""
        versions = ["v5.27.0", "v5.27.0-SNAPSHOT", "v5.26.0"]
        sorted_versions = sort_versions(versions)
        # SNAPSHOT should be oldest (dev release)
        assert sorted_versions[0] == "v5.27.0"
        assert "SNAPSHOT" in sorted_versions[1]

    def test_real_api_response(self):
        """Test realistic API response."""
        versions = [
            "v5.27.0",
            "v5.26.1",
            "v5.26.0",
            "v5.25.0-RC1",
            "5.27.0-beta",
            "v5.24.0",
            "v5.27.0-SNAPSHOT"
        ]
        sorted_versions = sort_versions(versions)
        # Latest stable should be first
        assert sorted_versions[0] == "v5.27.0"
        # 5.27.0 pre-releases should be after 5.27.0 stable but before 5.26.x
        assert "5.27.0-beta" in sorted_versions[1:3]
        assert "v5.27.0-SNAPSHOT" in sorted_versions[1:3]
        # v5.24.0 should be last stable release
        assert "v5.24.0" == sorted_versions[-1]


class TestGetLatestVersion:
    """Test getting latest version from list."""

    def test_get_latest_simple(self):
        """Test getting latest from simple list."""
        versions = ["v5.26.0", "v5.27.0", "v5.25.0"]
        assert get_latest_version(versions) == "v5.27.0"

    def test_get_latest_with_prereleases(self):
        """Test latest is stable release, not pre-release."""
        versions = ["v5.27.0-RC1", "v5.27.0", "v5.26.0"]
        assert get_latest_version(versions) == "v5.27.0"

    def test_get_latest_all_prereleases(self):
        """Test latest when all are pre-releases."""
        versions = ["v5.27.0-RC1", "v5.27.0-RC2", "v5.27.0-beta"]
        latest = get_latest_version(versions)
        # Should be RC2 (highest RC)
        assert "RC2" in latest

    def test_get_latest_mixed_formats(self):
        """Test latest with mixed formats."""
        versions = ["v5.27.0", "5.26.0", "v5.26.1"]
        assert get_latest_version(versions) == "v5.27.0"

    def test_empty_list(self):
        """Test empty list returns None."""
        assert get_latest_version([]) is None

    def test_all_invalid(self):
        """Test all invalid versions returns None."""
        versions = ["invalid", "bad_version", "not_a_version"]
        assert get_latest_version(versions) is None

    def test_preserves_original_format(self):
        """Test original format is preserved."""
        versions = ["v5.27.0", "5.26.0"]
        latest = get_latest_version(versions)
        assert latest == "v5.27.0"  # Original format with 'v'


class TestCompareVersions:
    """Test version comparison."""

    def test_greater_than(self):
        """Test version A > version B."""
        assert compare_versions("v5.27.0", "v5.26.0") == 1
        assert compare_versions("v5.27.1", "v5.27.0") == 1

    def test_less_than(self):
        """Test version A < version B."""
        assert compare_versions("v5.26.0", "v5.27.0") == -1
        assert compare_versions("v5.27.0", "v5.27.1") == -1

    def test_equal(self):
        """Test version A == version B."""
        assert compare_versions("v5.27.0", "v5.27.0") == 0
        assert compare_versions("v5.27.0", "5.27.0") == 0  # With/without 'v'

    def test_prerelease_less_than_release(self):
        """Test pre-release < release."""
        assert compare_versions("v5.27.0-RC1", "v5.27.0") == -1
        assert compare_versions("v5.27.0-beta", "v5.27.0") == -1

    def test_prerelease_comparison(self):
        """Test comparing pre-releases."""
        # RC2 > RC1
        assert compare_versions("v5.27.0-RC2", "v5.27.0-RC1") == 1
        # RC > beta (in PEP 440, rc > b)
        result = compare_versions("v5.27.0-RC1", "v5.27.0-beta")
        assert result == 1  # RC comes after beta in release cycle

    def test_invalid_version(self):
        """Test invalid version returns None."""
        assert compare_versions("invalid", "v5.27.0") is None
        assert compare_versions("v5.27.0", "bad_version") is None
        assert compare_versions("invalid", "bad_version") is None


class TestIsPrerelease:
    """Test pre-release detection."""

    def test_stable_release(self):
        """Test stable releases are not pre-release."""
        assert is_prerelease("v5.27.0") is False
        assert is_prerelease("5.27.0") is False

    def test_rc_prerelease(self):
        """Test RC versions are pre-release."""
        assert is_prerelease("v5.27.0-RC1") is True
        assert is_prerelease("5.27.0-rc2") is True

    def test_beta_prerelease(self):
        """Test beta versions are pre-release."""
        assert is_prerelease("v5.27.0-beta") is True
        assert is_prerelease("5.27.0-BETA") is True

    def test_alpha_prerelease(self):
        """Test alpha versions are pre-release."""
        assert is_prerelease("v5.27.0-alpha") is True
        assert is_prerelease("5.27.0-ALPHA") is True

    def test_snapshot_prerelease(self):
        """Test SNAPSHOT versions are pre-release (dev)."""
        assert is_prerelease("v5.27.0-SNAPSHOT") is True
        assert is_prerelease("5.27.0-snapshot") is True

    def test_invalid_version(self):
        """Test invalid versions are not pre-release."""
        assert is_prerelease("invalid") is False
        assert is_prerelease("bad_version") is False


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_coop_sweden_versions(self):
        """Test with actual Coop Sweden version patterns."""
        versions = [
            "v5.27.0",
            "v5.27.0-RC1",
            "v5.26.1",
            "v5.26.0",
            "v5.25.0",
            "v5.25.0-SNAPSHOT"
        ]
        sorted_versions = sort_versions(versions)
        assert sorted_versions[0] == "v5.27.0"
        assert sorted_versions[-1] == "v5.25.0-SNAPSHOT"  # Oldest pre-release

    def test_mixed_quality_data(self):
        """Test with mixed quality data (some invalid)."""
        versions = [
            "v5.27.0",
            "invalid_version",
            "v5.26.1",
            "",
            "v5.25.0-RC1",
            "5.x.y"
        ]
        sorted_versions = sort_versions(versions)
        # Valid versions first
        assert sorted_versions[0] == "v5.27.0"
        assert sorted_versions[1] == "v5.26.1"
        # Invalid versions at end
        invalid_count = sum(1 for v in sorted_versions[2:] if v in ["invalid_version", "", "5.x.y"])
        assert invalid_count == 3

    def test_version_range_selection(self):
        """Test selecting versions within a range."""
        versions = [
            "v5.30.0",
            "v5.27.0",
            "v5.26.1",
            "v5.26.0",
            "v5.25.0",
            "v5.24.0"
        ]
        sorted_versions = sort_versions(versions)

        # Get all versions >= 5.26.0
        from packaging.version import Version
        target_versions = []
        for v in sorted_versions:
            parsed, _ = parse_version_safe(v)
            if parsed and parsed >= Version("5.26.0"):
                target_versions.append(v)

        assert len(target_versions) == 4  # 5.30, 5.27, 5.26.1, 5.26.0
        assert "v5.24.0" not in target_versions
        assert "v5.25.0" not in target_versions
