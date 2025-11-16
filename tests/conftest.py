"""
Pytest configuration and fixtures for Store-Install-Builder tests
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Add the gk_install_builder package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_config_manager():
    """Provide a mock ConfigManager with default configuration"""
    mock = Mock()
    mock.config = {
        "platform": "Windows",
        "base_url": "test.example.cloud4retail.co",
        "base_install_dir": "C:\\gkretail",
        "project_name": "Test Project",
        "version": "v1.0.0",
        "tenant_id": "001",
        "use_hostname_detection": True,
        "use_file_detection": False,
        "hostname_pattern_windows": "(?P<store>\\d{4})-(?P<workstation>\\d{3})",
        "hostname_pattern_linux": "(?P<store>\\d{4})-(?P<workstation>\\d{3})",
        "ssl_password": "changeit",
        "certificate_path": "PROJECT/BASEURL/certificate.p12",
        "output_dir": "PROJECT/BASEURL",
        "pos_version": "v1.0.0",
        "wdm_version": "v1.0.0",
        "flow_service_version": "v1.0.0",
        "lpa_service_version": "v1.0.0",
        "storehub_service_version": "v1.0.0",
        "environments": [],
    }
    mock.get_entry = Mock(return_value=None)
    mock.save_config = Mock()
    mock.update_config_from_entries = Mock()
    mock.register_entry = Mock()
    mock.unregister_entry = Mock()
    return mock


@pytest.fixture
def mock_project_generator():
    """Provide a mock ProjectGenerator"""
    mock = Mock()
    mock.generate_project = Mock(return_value=True)
    mock.generate = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_detection_manager():
    """Provide a mock DetectionManager"""
    mock = Mock()
    mock.validate_hostname_regex = Mock(return_value=(True, ""))
    mock.test_hostname_regex = Mock(return_value=(True, "R001", "101", None))
    return mock


@pytest.fixture
def sample_config():
    """Provide sample configuration dictionary"""
    return {
        "platform": "Windows",
        "base_url": "dev.cse.cloud4retail.co",
        "base_install_dir": "C:\\gkretail",
        "project_name": "CSE Project",
        "version": "v2.0.0",
        "tenant_id": "001",
        "use_hostname_detection": True,
        "use_file_detection": False,
        "ssl_password": "changeit",
        "include_pos": True,
        "include_wdm": True,
        "include_flow_service": False,
        "include_lpa_service": False,
        "include_storehub_service": False,
    }


@pytest.fixture
def sample_environment():
    """Provide sample environment configuration"""
    return {
        "alias": "DEV",
        "name": "Development",
        "base_url": "dev.example.cloud4retail.co",
        "use_default_tenant": False,
        "tenant_id": "001",
        "launchpad_oauth2": "ZW5jb2RlZF9wYXNzd29yZA==",
        "eh_launchpad_username": "1001",
        "eh_launchpad_password": "password123",
    }


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing"""
    config_path = tmp_path / "gk_install_config.json"
    return config_path


@pytest.fixture
def mock_requests():
    """Mock requests library for API testing"""
    with patch('requests.post') as mock_post, \
         patch('requests.get') as mock_get:
        # Default successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token_123"}
        mock_response.text = '{"access_token": "test_token_123"}'

        mock_post.return_value = mock_response
        mock_get.return_value = mock_response

        yield {"post": mock_post, "get": mock_get, "response": mock_response}


@pytest.fixture
def mock_ctk_window():
    """Mock CustomTkinter window for GUI testing"""
    with patch('customtkinter.CTk') as mock_ctk:
        mock_window = Mock()
        mock_window.title = Mock()
        mock_window.geometry = Mock()
        mock_window.protocol = Mock()
        mock_ctk.return_value = mock_window
        yield mock_window


@pytest.fixture
def platform_windows():
    """Mock Windows platform"""
    with patch('sys.platform', 'win32'):
        yield


@pytest.fixture
def platform_linux():
    """Mock Linux platform"""
    with patch('sys.platform', 'linux'):
        yield
