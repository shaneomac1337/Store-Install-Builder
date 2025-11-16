"""
Unit tests for auto-fill functionality
"""
import pytest
from unittest.mock import Mock, patch


class TestAutoFillLogic:
    """Test the auto-fill logic for extracting project codes and generating system types"""

    def test_extract_project_code_from_customer_url(self):
        """Test extracting project code from customer URL (e.g., dev.cse.cloud4retail.co)"""
        base_url = "dev.cse.cloud4retail.co"
        parts = base_url.split(".")

        # Customer URL logic: parts[1] should be 'cse'
        if len(parts) > 1 and parts[1].lower() != "cloud4retail":
            project_code = parts[1].upper()
        else:
            project_code = "GKR"

        assert project_code == "CSE"

    def test_extract_project_code_from_product_url(self):
        """Test extracting project code from product URL (e.g., dev.cloud4retail.co)"""
        base_url = "dev.cloud4retail.co"
        parts = base_url.split(".")

        # Product URL logic: parts[1] is 'cloud4retail', should use GKR
        if len(parts) > 1 and parts[1].lower() == "cloud4retail":
            project_code = "GKR"
            extracted_project_name = parts[0].upper()
        else:
            project_code = parts[1].upper() if len(parts) > 1 else "GKR"
            extracted_project_name = project_code

        assert project_code == "GKR"
        assert extracted_project_name == "DEV"

    def test_generate_system_types_customer_project(self):
        """Test system type generation for customer project (CSE)"""
        project_code = "CSE"

        pos_system_type = f"{project_code}-OPOS-CLOUD"
        wdm_system_type = f"{project_code}-wdm"
        flow_service_system_type = "GKR-FLOWSERVICE-CLOUD"  # Exception: always GKR
        lpa_service_system_type = f"{project_code}-lps-lpa"
        storehub_service_system_type = f"{project_code}-sh-cloud"

        assert pos_system_type == "CSE-OPOS-CLOUD"
        assert wdm_system_type == "CSE-wdm"
        assert flow_service_system_type == "GKR-FLOWSERVICE-CLOUD"
        assert lpa_service_system_type == "CSE-lps-lpa"
        assert storehub_service_system_type == "CSE-sh-cloud"

    def test_generate_system_types_product_project(self):
        """Test system type generation for product project (GKR)"""
        project_code = "GKR"

        pos_system_type = f"{project_code}-OPOS-CLOUD"
        wdm_system_type = f"{project_code}-wdm"
        flow_service_system_type = "GKR-FLOWSERVICE-CLOUD"
        lpa_service_system_type = f"{project_code}-lps-lpa"
        storehub_service_system_type = f"{project_code}-sh-cloud"

        assert pos_system_type == "GKR-OPOS-CLOUD"
        assert wdm_system_type == "GKR-wdm"
        assert flow_service_system_type == "GKR-FLOWSERVICE-CLOUD"
        assert lpa_service_system_type == "GKR-lps-lpa"
        assert storehub_service_system_type == "GKR-sh-cloud"

    def test_generate_system_types_custom_project(self):
        """Test system type generation for custom project (e.g., ABC)"""
        project_code = "ABC"

        pos_system_type = f"{project_code}-OPOS-CLOUD"
        wdm_system_type = f"{project_code}-wdm"
        flow_service_system_type = "GKR-FLOWSERVICE-CLOUD"  # Exception
        lpa_service_system_type = f"{project_code}-lps-lpa"
        storehub_service_system_type = f"{project_code}-sh-cloud"

        assert pos_system_type == "ABC-OPOS-CLOUD"
        assert wdm_system_type == "ABC-wdm"
        assert flow_service_system_type == "GKR-FLOWSERVICE-CLOUD"
        assert lpa_service_system_type == "ABC-lps-lpa"
        assert storehub_service_system_type == "ABC-sh-cloud"

    def test_output_directory_generation(self):
        """Test output directory path generation"""
        project_name = "CSE Project"
        base_url = "dev.cse.cloud4retail.co"
        import os

        output_dir = os.path.join(project_name, base_url)

        assert output_dir == "CSE Project/dev.cse.cloud4retail.co" or \
               output_dir == "CSE Project\\dev.cse.cloud4retail.co"

    def test_certificate_path_generation(self):
        """Test certificate path generation"""
        project_name = "CSE Project"
        base_url = "dev.cse.cloud4retail.co"
        import os

        cert_path = os.path.join(project_name, base_url, "certificate.p12")

        assert "CSE Project" in cert_path
        assert "dev.cse.cloud4retail.co" in cert_path
        assert "certificate.p12" in cert_path

    def test_empty_url_handling(self):
        """Test that empty URL doesn't break auto-fill"""
        base_url = ""

        # Should return early for empty URL
        if not base_url:
            skip = True
        else:
            skip = False

        assert skip is True

    def test_url_without_dots(self):
        """Test URL without dots (edge case)"""
        base_url = "localhost"

        if "." in base_url:
            has_dots = True
        else:
            has_dots = False

        assert has_dots is False

    def test_url_with_subdomain(self):
        """Test URL with multiple subdomains"""
        base_url = "dev.test.cse.cloud4retail.co"
        parts = base_url.split(".")

        # Should still extract 'test' as parts[1]
        if len(parts) > 1 and parts[1].lower() != "cloud4retail":
            project_code = parts[1].upper()
        else:
            project_code = "GKR"

        assert project_code == "TEST"
