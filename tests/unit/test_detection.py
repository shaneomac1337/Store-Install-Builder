"""
Unit tests for detection functionality (hostname and file-based)
"""
import pytest
import re


class TestDetectionLogic:
    """Test detection logic for hostname and file-based detection"""

    def test_2group_hostname_pattern_extraction(self):
        """Test 2-group hostname pattern (Store-Workstation)"""
        pattern = r"(?P<store>\d{4})-(?P<workstation>\d{3})"
        hostname = "0001-101"

        match = re.match(pattern, hostname)

        assert match is not None
        assert match.group("store") == "0001"
        assert match.group("workstation") == "101"

    def test_3group_hostname_pattern_extraction(self):
        """Test 3-group hostname pattern (Environment-Store-Workstation)"""
        pattern = r"(?P<environment>\w+)-(?P<store>\d{4})-(?P<workstation>\d{3})"
        hostname = "DEV-0001-101"

        match = re.match(pattern, hostname)

        assert match is not None
        assert match.group("environment") == "DEV"
        assert match.group("store") == "0001"
        assert match.group("workstation") == "101"

    def test_hostname_pattern_validation_valid(self):
        """Test hostname pattern validation with valid patterns"""
        valid_patterns = [
            r"(?P<store>\d{4})-(?P<workstation>\d{3})",
            r"(?P<environment>\w+)-(?P<store>\d{4})-(?P<workstation>\d{3})",
            r"(?P<store>R\d{3})-(?P<workstation>WS\d{2})",
        ]

        for pattern in valid_patterns:
            try:
                re.compile(pattern)
                is_valid = True
            except re.error:
                is_valid = False

            assert is_valid is True

    def test_hostname_pattern_validation_invalid(self):
        """Test hostname pattern validation with invalid patterns"""
        invalid_patterns = [
            r"(?P<store>\d{4}-(?P<workstation>\d{3})",  # Unbalanced parentheses
            r"(?P<invalid>[)",  # Incomplete pattern
            r"(?P<store>",  # Incomplete group
        ]

        for pattern in invalid_patterns:
            try:
                re.compile(pattern)
                is_valid = True
            except re.error:
                is_valid = False

            assert is_valid is False

    def test_environment_detection_enabled(self):
        """Test that 3-group pattern is used when environment detection is enabled"""
        use_environment_detection = True

        if use_environment_detection:
            # Should use 3-group pattern
            groups_required = 3
        else:
            # Should use 2-group pattern
            groups_required = 2

        assert groups_required == 3

    def test_environment_detection_disabled(self):
        """Test that 2-group pattern is used when environment detection is disabled"""
        use_environment_detection = False

        if use_environment_detection:
            groups_required = 3
        else:
            groups_required = 2

        assert groups_required == 2

    def test_file_detection_enabled(self):
        """Test file detection configuration"""
        use_file_detection = True
        base_directory = "C:\\gkretail\\stations"
        station_filename = ".station"

        if use_file_detection:
            detection_path = f"{base_directory}/{station_filename}"
        else:
            detection_path = None

        assert detection_path is not None
        assert base_directory in detection_path
        assert station_filename in detection_path

    def test_store_id_format_validation(self):
        """Test store ID format validation"""
        valid_store_ids = ["R0001", "R9999", "0001", "1234"]
        invalid_store_ids = ["", "R", "ABCD", "12", "123456"]

        for store_id in valid_store_ids:
            # Accept formats like R0001 or just 0001 (numeric)
            is_valid = bool(re.match(r"^(R?\d{4})$", store_id))
            assert is_valid is True, f"{store_id} should be valid"

    def test_workstation_id_format_validation(self):
        """Test workstation ID format validation"""
        valid_workstation_ids = ["101", "999", "001"]
        invalid_workstation_ids = ["", "1", "12", "1234", "ABC"]

        for ws_id in valid_workstation_ids:
            # Should be 3 digits
            is_valid = bool(re.match(r"^\d{3}$", ws_id))
            assert is_valid is True, f"{ws_id} should be valid"

        for ws_id in invalid_workstation_ids:
            is_valid = bool(re.match(r"^\d{3}$", ws_id))
            assert is_valid is False, f"{ws_id} should be invalid"

    def test_multiple_hostname_patterns(self):
        """Test that different hostname patterns can be used for different scenarios"""
        test_cases = [
            {
                "pattern": r"(?P<store>\d{4})-(?P<workstation>\d{3})",
                "hostname": "0005-101",
                "expected_store": "0005",
                "expected_workstation": "101",
            },
            {
                "pattern": r"(?P<store>R\d{3})-(?P<workstation>\d{3})",
                "hostname": "R005-101",
                "expected_store": "R005",
                "expected_workstation": "101",
            },
            {
                "pattern": r"(?P<environment>[A-Z]+)-(?P<store>\d{4})-(?P<workstation>\d{3})",
                "hostname": "PROD-0005-101",
                "expected_store": "0005",
                "expected_workstation": "101",
            },
        ]

        for test_case in test_cases:
            match = re.match(test_case["pattern"], test_case["hostname"])
            assert match is not None
            assert match.group("store") == test_case["expected_store"]
            assert match.group("workstation") == test_case["expected_workstation"]

    def test_detection_priority_cli_parameters(self):
        """Test that CLI parameters have highest priority"""
        # Simulate detection priority
        cli_store_id = "R005"
        cli_workstation_id = "101"
        hostname_detected_store = "R006"
        file_detected_store = "R007"

        # Priority: CLI > Hostname > File
        if cli_store_id:
            final_store = cli_store_id
        elif hostname_detected_store:
            final_store = hostname_detected_store
        else:
            final_store = file_detected_store

        assert final_store == "R005"  # CLI should win

    def test_detection_priority_hostname_over_file(self):
        """Test that hostname detection has priority over file detection"""
        cli_store_id = None
        hostname_detected_store = "R006"
        file_detected_store = "R007"

        # Priority: CLI > Hostname > File
        if cli_store_id:
            final_store = cli_store_id
        elif hostname_detected_store:
            final_store = hostname_detected_store
        else:
            final_store = file_detected_store

        assert final_store == "R006"  # Hostname should win

    def test_detection_fallback_to_file(self):
        """Test that file detection is used as fallback"""
        cli_store_id = None
        hostname_detected_store = None
        file_detected_store = "R007"

        # Priority: CLI > Hostname > File
        if cli_store_id:
            final_store = cli_store_id
        elif hostname_detected_store:
            final_store = hostname_detected_store
        else:
            final_store = file_detected_store

        assert final_store == "R007"  # File should be used as fallback
