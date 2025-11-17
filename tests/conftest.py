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


# ============================================================================
# Generator-Specific Fixtures for Phase 0 Testing
# ============================================================================

@pytest.fixture
def sample_templates(tmp_path):
    """Create minimal template files for testing"""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    # Create simple PowerShell template
    ps1_template = template_dir / "simple.ps1.template"
    ps1_template.write_text("""# Test Template
$BASE_URL = "@BASE_URL@"
$INSTALL_DIR = "@BASE_INSTALL_DIR@"
$VERSION = "@VERSION@"
$TENANT_ID = "@TENANT_ID@"
# HOSTNAME_ENV_DETECTION_PLACEHOLDER
""")

    # Create simple Bash template
    sh_template = template_dir / "simple.sh.template"
    sh_template.write_text("""#!/bin/bash
BASE_URL="@BASE_URL@"
INSTALL_DIR="@BASE_INSTALL_DIR@"
VERSION="@VERSION@"
TENANT_ID="@TENANT_ID@"
# HOSTNAME_ENV_DETECTION_PLACEHOLDER
""")

    # Create launcher template
    launcher_template = template_dir / "launcher.template"
    launcher_template.write_text("""{
  "component": "@COMPONENT_NAME@",
  "version": "@COMPONENT_VERSION@",
  "baseUrl": "@BASE_URL@"
}""")

    return template_dir


@pytest.fixture
def sample_config_windows():
    """Provide minimal Windows configuration for testing"""
    return {
        "platform": "Windows",
        "base_url": "test.cloud4retail.co",
        "base_install_dir": "C:\\gkretail",
        "project_name": "Test Project",
        "version": "v1.0.0",
        "tenant_id": "001",
        "output_dir": "test_output",
        "ssl_password": "changeit",
        "system_type": "GKR-POS-CLOUD",
        "include_pos": True,
        "include_wdm": False,
        "include_flow_service": False,
        "include_lpa_service": False,
        "include_storehub_service": False,
        "use_hostname_detection": False,
        "use_file_detection": False,
        "pos_version": "v1.0.0",
        "certificate_path": "",
        "environments": []
    }


@pytest.fixture
def sample_config_linux():
    """Provide minimal Linux configuration for testing"""
    return {
        "platform": "Linux",
        "base_url": "test.cloud4retail.co",
        "base_install_dir": "/usr/local/gkretail",
        "project_name": "Test Project Linux",
        "version": "v1.0.0",
        "tenant_id": "001",
        "output_dir": "test_output_linux",
        "ssl_password": "changeit",
        "system_type": "GKR-POS-CLOUD",
        "include_pos": True,
        "include_wdm": False,
        "include_flow_service": False,
        "include_lpa_service": False,
        "include_storehub_service": False,
        "use_hostname_detection": False,
        "use_file_detection": False,
        "pos_version": "v1.0.0",
        "certificate_path": "",
        "environments": []
    }


@pytest.fixture
def sample_config_multi_env():
    """Provide multi-environment configuration for testing"""
    return {
        "platform": "Windows",
        "base_url": "dev.cloud4retail.co",
        "base_install_dir": "C:\\gkretail",
        "project_name": "Multi-Env Project",
        "version": "v1.5.0",
        "tenant_id": "005",
        "output_dir": "test_output_multi",
        "ssl_password": "multienv123",
        "system_type": "GKR-POS-CLOUD",
        "include_pos": True,
        "include_wdm": True,
        "use_hostname_detection": True,
        "hostname_pattern_windows": "^(\\w+)-POS-(\\d{4})-(\\d{3})$",
        "pos_version": "v1.5.0",
        "wdm_version": "v1.2.0",
        "environments": [
            {
                "alias": "DEV",
                "name": "Development",
                "base_url": "dev.cloud4retail.co",
                "tenant_id": "001",
                "launchpad_oauth2": "devpass123",
                "eh_launchpad_username": "1001",
                "eh_launchpad_password": "ehdev001"
            },
            {
                "alias": "PROD",
                "name": "Production",
                "base_url": "prod.cloud4retail.co",
                "tenant_id": "002",
                "launchpad_oauth2": "prodpass456",
                "eh_launchpad_username": "2001",
                "eh_launchpad_password": "ehprod002"
            }
        ]
    }


@pytest.fixture
def generator_no_gui(mocker):
    """Provide ProjectGenerator instance without GUI dependencies"""
    from gk_install_builder.generator import ProjectGenerator

    # Mock the parent_window to None
    generator = ProjectGenerator(parent_window=None)

    # Mock any GUI dialog methods
    generator._show_error = Mock()
    generator._show_success = Mock()
    generator._show_info = Mock()

    return generator


@pytest.fixture
def mock_detection_manager_configured(mocker):
    """Provide a configured DetectionManager mock for testing"""
    from gk_install_builder.detection import DetectionManager

    mock = Mock(spec=DetectionManager)

    # Configure detection settings
    mock.is_detection_enabled.return_value = True
    mock.get_file_path.return_value = "C:\\gkretail\\stations\\POS.station"
    mock.get_base_directory.return_value = "C:\\gkretail"
    mock.detection_config = {
        "use_hostname_detection": True,
        "use_file_detection": True,
        "hostname_pattern_windows": "^POS-(\\d{4})-(\\d{3})$",
        "hostname_pattern_linux": "^pos-(\\d{4})-(\\d{3})$",
        "detection_files": {
            "POS": "stations\\POS.station",
            "WDM": "stations\\WDM.station",
            "Flow": "stations\\Flow.station",
            "LPA": "stations\\LPA.station",
            "StoreHub": "stations\\StoreHub.station"
        }
    }

    return mock


@pytest.fixture
def temp_output_dir(tmp_path):
    """Provide a temporary output directory for generation testing"""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_template_dir(tmp_path, monkeypatch):
    """Mock the template directory path to use test templates"""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    # Create minimal templates
    (template_dir / "GKInstall.ps1.template").write_text("""
# Test PowerShell Template
$BASE_URL = "@BASE_URL@"
$INSTALL_DIR = "@BASE_INSTALL_DIR@"
# HOSTNAME_ENV_DETECTION_PLACEHOLDER
""")

    (template_dir / "GKInstall.sh.template").write_text("""
#!/bin/bash
# Test Bash Template
BASE_URL="@BASE_URL@"
INSTALL_DIR="@BASE_INSTALL_DIR@"
# HOSTNAME_ENV_DETECTION_PLACEHOLDER
""")

    # Patch the template directory in ProjectGenerator
    # This will be used by tests that instantiate ProjectGenerator
    import gk_install_builder.generator as generator_module
    monkeypatch.setattr(generator_module, 'os', Mock())

    return template_dir


@pytest.fixture(autouse=True, scope="function")
def mock_detection_import():
    """
    Auto-mock the detection module to handle relative imports in generator.py

    This fixture runs automatically for all tests and mocks the 'detection'
    module that generator.py imports. This is necessary because generator.py
    uses 'from detection import DetectionManager' (relative import).
    """
    # Save original if it exists
    original_detection = sys.modules.get('detection')

    # Create mock detection module
    mock_detection_module = Mock()
    mock_detection_class = Mock()

    # Configure the mock DetectionManager class
    mock_detection_instance = Mock()
    mock_detection_instance.enable_file_detection = Mock()
    mock_detection_class.return_value = mock_detection_instance

    mock_detection_module.DetectionManager = mock_detection_class
    sys.modules['detection'] = mock_detection_module

    yield mock_detection_class

    # Restore original or remove mock
    if original_detection is not None:
        sys.modules['detection'] = original_detection
    else:
        sys.modules.pop('detection', None)
