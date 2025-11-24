"""
Version sorting utilities for handling component version strings.

This module provides robust version comparison and sorting functionality
for retail software component versions returned from APIs.

Supports various version formats:
- Standard semver: v5.27.0, 5.27.0, v5.26.1
- Pre-release tags: v5.25.0-RC1, v5.25.0-beta, v5.25.0-SNAPSHOT
- Build metadata: v5.27.0+build123
- Incomplete versions: v5.27, 5.27 (missing patch)
"""

from typing import List, Optional, Tuple
from packaging.version import Version, InvalidVersion
import logging

logger = logging.getLogger(__name__)


def normalize_version_string(version_str: str) -> str:
    """
    Normalize a version string by removing common prefixes and handling edge cases.

    Args:
        version_str: Raw version string (e.g., "v5.27.0", "5.27.0-RC1")

    Returns:
        Normalized version string suitable for parsing

    Examples:
        >>> normalize_version_string("v5.27.0")
        "5.27.0"
        >>> normalize_version_string("5.27")
        "5.27.0"
        >>> normalize_version_string("v5.25.0-RC1")
        "5.25.0rc1"
    """
    # Remove leading 'v' or 'V' prefix
    normalized = version_str.strip()
    if normalized.lower().startswith('v'):
        normalized = normalized[1:]

    # Handle incomplete versions (missing patch number)
    # e.g., "5.27" -> "5.27.0"
    parts = normalized.split('-')[0].split('+')[0]  # Get base version before pre-release/build
    version_parts = parts.split('.')
    if len(version_parts) == 2:
        # Add patch version if missing
        base = '.'.join(version_parts) + '.0'
        # Re-add pre-release and build metadata if present
        if '-' in normalized:
            base += '-' + normalized.split('-', 1)[1]
        elif '+' in normalized:
            base += '+' + normalized.split('+', 1)[1]
        normalized = base

    # Normalize pre-release tags to PEP 440 format
    # RC, SNAPSHOT, alpha, beta should be recognized
    # PEP 440 uses: a (alpha), b (beta), rc (release candidate)
    normalized = normalized.replace('-SNAPSHOT', '.dev0')  # SNAPSHOT -> dev release
    normalized = normalized.replace('-snapshot', '.dev0')
    normalized = normalized.replace('-RC', 'rc')  # RC1 -> rc1
    normalized = normalized.replace('-rc', 'rc')
    normalized = normalized.replace('-beta', 'b')
    normalized = normalized.replace('-BETA', 'b')
    normalized = normalized.replace('-alpha', 'a')
    normalized = normalized.replace('-ALPHA', 'a')

    return normalized


def parse_version_safe(version_str: str) -> Tuple[Optional[Version], str]:
    """
    Safely parse a version string, handling invalid formats gracefully.

    Args:
        version_str: Version string to parse

    Returns:
        Tuple of (parsed Version object or None, original string)

    Examples:
        >>> version, original = parse_version_safe("v5.27.0")
        >>> version.major
        5
        >>> original
        "v5.27.0"
    """
    try:
        normalized = normalize_version_string(version_str)
        version_obj = Version(normalized)
        return (version_obj, version_str)
    except InvalidVersion as e:
        logger.warning(f"Invalid version format '{version_str}': {e}")
        return (None, version_str)
    except Exception as e:
        logger.error(f"Unexpected error parsing version '{version_str}': {e}")
        return (None, version_str)


def sort_versions(version_list: List[str], descending: bool = True) -> List[str]:
    """
    Sort a list of version strings from newest to oldest (or vice versa).

    Invalid version strings are placed at the end of the sorted list.

    Args:
        version_list: List of version strings to sort
        descending: If True, sort newest to oldest (default). If False, oldest to newest.

    Returns:
        Sorted list of version strings (original format preserved)

    Examples:
        >>> versions = ["v5.27.0", "v5.26.1", "v5.27.0-RC1", "5.26.0"]
        >>> sort_versions(versions)
        ["v5.27.0", "v5.26.1", "5.26.0", "v5.27.0-RC1"]

        >>> sort_versions(versions, descending=False)
        ["v5.27.0-RC1", "5.26.0", "v5.26.1", "v5.27.0"]
    """
    if not version_list:
        return []

    # Parse all versions
    parsed_versions = [parse_version_safe(v) for v in version_list]

    # Separate valid and invalid versions
    valid_versions = [(v, orig) for v, orig in parsed_versions if v is not None]
    invalid_versions = [orig for v, orig in parsed_versions if v is None]

    # Sort valid versions
    valid_versions.sort(key=lambda x: x[0], reverse=descending)

    # Combine: valid versions first, then invalid versions at the end
    sorted_list = [orig for v, orig in valid_versions] + invalid_versions

    if invalid_versions:
        logger.info(f"Sorted {len(valid_versions)} valid versions, "
                   f"{len(invalid_versions)} invalid versions placed at end")

    return sorted_list


def get_latest_version(version_list: List[str]) -> Optional[str]:
    """
    Get the latest (highest) version from a list of version strings.

    Args:
        version_list: List of version strings

    Returns:
        Latest version string in original format, or None if list is empty or all invalid

    Examples:
        >>> versions = ["v5.27.0", "v5.26.1", "v5.27.0-RC1", "5.26.0"]
        >>> get_latest_version(versions)
        "v5.27.0"

        >>> get_latest_version(["v5.27.0-RC1", "v5.27.0-beta"])
        "v5.27.0-RC1"
    """
    if not version_list:
        logger.warning("Empty version list provided to get_latest_version")
        return None

    sorted_versions = sort_versions(version_list, descending=True)

    if not sorted_versions:
        logger.warning("No valid versions found in list")
        return None

    latest = sorted_versions[0]

    # Verify the latest version is actually valid (not from the invalid group)
    parsed, _ = parse_version_safe(latest)
    if parsed is None:
        logger.warning(f"Latest version '{latest}' could not be parsed as valid version")
        return None

    logger.debug(f"Latest version identified: {latest}")
    return latest


def compare_versions(version_a: str, version_b: str) -> int:
    """
    Compare two version strings.

    Args:
        version_a: First version string
        version_b: Second version string

    Returns:
        -1 if version_a < version_b
         0 if version_a == version_b
         1 if version_a > version_b
         None if either version is invalid

    Examples:
        >>> compare_versions("v5.27.0", "v5.26.1")
        1
        >>> compare_versions("v5.27.0-RC1", "v5.27.0")
        -1
        >>> compare_versions("5.27.0", "v5.27.0")
        0
    """
    parsed_a, _ = parse_version_safe(version_a)
    parsed_b, _ = parse_version_safe(version_b)

    if parsed_a is None or parsed_b is None:
        logger.warning(f"Cannot compare invalid versions: '{version_a}' vs '{version_b}'")
        return None

    if parsed_a < parsed_b:
        return -1
    elif parsed_a > parsed_b:
        return 1
    else:
        return 0


def is_prerelease(version_str: str) -> bool:
    """
    Check if a version string represents a pre-release version.

    Pre-release versions include: RC, beta, alpha, SNAPSHOT, dev

    Args:
        version_str: Version string to check

    Returns:
        True if version is a pre-release, False otherwise

    Examples:
        >>> is_prerelease("v5.27.0-RC1")
        True
        >>> is_prerelease("v5.27.0")
        False
        >>> is_prerelease("v5.27.0-SNAPSHOT")
        True
    """
    parsed, _ = parse_version_safe(version_str)
    if parsed is None:
        return False

    # Check if version has any pre-release components
    return parsed.is_prerelease or parsed.is_devrelease


# Example usage and testing
if __name__ == "__main__":
    # Configure logging for standalone testing
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

    print("=" * 70)
    print("Version Sorting Utility - Test Examples")
    print("=" * 70)

    # Example 1: Typical API response
    print("\nExample 1: Typical API response (unsorted)")
    versions = [
        "v5.27.0",
        "v5.26.1",
        "v5.26.0",
        "v5.25.0-RC1",
        "5.27.0-beta",
        "v5.24.0",
        "v5.27.0-SNAPSHOT"
    ]
    print(f"Input:  {versions}")
    sorted_versions = sort_versions(versions)
    print(f"Sorted: {sorted_versions}")
    latest = get_latest_version(versions)
    print(f"Latest: {latest}")

    # Example 2: Pre-release handling
    print("\n" + "-" * 70)
    print("Example 2: Pre-release version comparison")
    versions = ["v5.27.0", "v5.27.0-RC1", "v5.27.0-RC2", "v5.27.0-beta"]
    print(f"Versions: {versions}")
    for v in versions:
        print(f"  {v:20s} - Pre-release: {is_prerelease(v)}")
    sorted_versions = sort_versions(versions)
    print(f"Sorted:   {sorted_versions}")

    # Example 3: Mixed formats
    print("\n" + "-" * 70)
    print("Example 3: Mixed formats (with/without 'v' prefix)")
    versions = ["v5.27.0", "5.26.1", "v5.26.0", "5.27.0-RC1"]
    print(f"Input:  {versions}")
    sorted_versions = sort_versions(versions)
    print(f"Sorted: {sorted_versions}")

    # Example 4: Incomplete versions
    print("\n" + "-" * 70)
    print("Example 4: Incomplete versions (missing patch)")
    versions = ["v5.27", "v5.26.1", "5.27.0"]
    print(f"Input:  {versions}")
    sorted_versions = sort_versions(versions)
    print(f"Sorted: {sorted_versions}")

    # Example 5: Version comparison
    print("\n" + "-" * 70)
    print("Example 5: Direct version comparison")
    comparisons = [
        ("v5.27.0", "v5.26.1"),
        ("v5.27.0-RC1", "v5.27.0"),
        ("5.27.0", "v5.27.0"),
        ("v5.27.0-beta", "v5.27.0-RC1")
    ]
    for v1, v2 in comparisons:
        result = compare_versions(v1, v2)
        symbol = ">" if result == 1 else "=" if result == 0 else "<"
        print(f"  {v1:20s} {symbol} {v2}")

    # Example 6: Invalid versions
    print("\n" + "-" * 70)
    print("Example 6: Handling invalid versions")
    versions = ["v5.27.0", "invalid", "v5.26.1", "5.x.y", "v5.25.0"]
    print(f"Input:  {versions}")
    sorted_versions = sort_versions(versions)
    print(f"Sorted: {sorted_versions}")
    print("(Invalid versions placed at end)")

    print("\n" + "=" * 70)
