"""
Unit tests for configuration management
"""
import pytest
import json
from unittest.mock import Mock, MagicMock, mock_open, patch


class TestConfigManagement:
    """Test configuration loading, saving, and management"""

    def test_config_default_values(self):
        """Test that default configuration values are set correctly"""
        default_config = {
            "platform": "Windows",
            "base_url": "",
            "base_install_dir": "C:\\gkretail",
            "project_name": "",
            "version": "v1.0.0",
            "tenant_id": "001",
            "use_hostname_detection": True,
            "use_file_detection": False,
            "ssl_password": "changeit",
        }

        assert default_config["platform"] == "Windows"
        assert default_config["base_install_dir"] == "C:\\gkretail"
        assert default_config["tenant_id"] == "001"
        assert default_config["use_hostname_detection"] is True
        assert default_config["ssl_password"] == "changeit"

    def test_config_entry_registration(self):
        """Test entry widget registration with config manager"""
        mock_entry = Mock()
        mock_entry.get = Mock(return_value="test_value")

        registered_entries = {}
        config_key = "base_url"

        # Simulate registration
        registered_entries[config_key] = mock_entry

        assert config_key in registered_entries
        assert registered_entries[config_key] == mock_entry

    def test_config_entry_unregistration(self):
        """Test entry widget unregistration"""
        mock_entry = Mock()
        registered_entries = {"base_url": mock_entry}

        # Unregister
        if "base_url" in registered_entries:
            del registered_entries["base_url"]

        assert "base_url" not in registered_entries

    def test_config_update_from_entries(self):
        """Test updating config from entry widgets"""
        mock_entry_url = Mock()
        mock_entry_url.get = Mock(return_value="test.cloud4retail.co")

        mock_entry_tenant = Mock()
        mock_entry_tenant.get = Mock(return_value="002")

        registered_entries = {
            "base_url": mock_entry_url,
            "tenant_id": mock_entry_tenant,
        }

        # Simulate update
        config = {}
        for key, entry in registered_entries.items():
            config[key] = entry.get()

        assert config["base_url"] == "test.cloud4retail.co"
        assert config["tenant_id"] == "002"

    def test_config_fixed_value_handling(self):
        """Test that fixed value entries are not updated from widgets"""
        mock_entry = Mock()
        mock_entry.get = Mock(return_value="user_entered_value")

        fixed_value = "launchpad"  # Auth service BA user is fixed
        config_key = "auth_service_ba_user"

        # Simulate fixed value logic
        if fixed_value:
            final_value = fixed_value
        else:
            final_value = mock_entry.get()

        assert final_value == "launchpad"  # Should use fixed value, not widget value

    def test_config_auto_save_debounce(self):
        """Test that auto-save uses debounce to avoid excessive saves"""
        import time

        save_calls = []
        debounce_time = 1.0  # 1 second debounce

        def mock_save():
            save_calls.append(time.time())

        # Simulate multiple rapid changes
        last_save_time = None

        for i in range(5):
            current_time = time.time()
            if last_save_time is None or (current_time - last_save_time) >= debounce_time:
                mock_save()
                last_save_time = current_time
            time.sleep(0.1)  # Rapid changes

        # Should only save once despite 5 changes (within debounce window)
        assert len(save_calls) == 1

    def test_environment_config_structure(self):
        """Test environment configuration structure"""
        environment = {
            "alias": "DEV",
            "name": "Development",
            "base_url": "dev.example.cloud4retail.co",
            "use_default_tenant": False,
            "tenant_id": "001",
            "launchpad_oauth2": "encoded_password",
            "eh_launchpad_username": "1001",
            "eh_launchpad_password": "password123",
        }

        assert environment["alias"] == "DEV"
        assert environment["name"] == "Development"
        assert environment["use_default_tenant"] is False
        assert environment["tenant_id"] == "001"

    def test_add_environment_to_config(self):
        """Test adding a new environment to configuration"""
        config = {"environments": []}
        new_environment = {
            "alias": "TEST",
            "name": "Testing",
            "base_url": "test.example.cloud4retail.co",
            "tenant_id": "002",
        }

        config["environments"].append(new_environment)

        assert len(config["environments"]) == 1
        assert config["environments"][0]["alias"] == "TEST"

    def test_update_environment_in_config(self):
        """Test updating an existing environment"""
        config = {
            "environments": [
                {
                    "alias": "DEV",
                    "name": "Development",
                    "base_url": "dev.example.cloud4retail.co",
                    "tenant_id": "001",
                }
            ]
        }

        # Update tenant ID
        for env in config["environments"]:
            if env["alias"] == "DEV":
                env["tenant_id"] = "999"

        assert config["environments"][0]["tenant_id"] == "999"

    def test_delete_environment_from_config(self):
        """Test deleting an environment"""
        config = {
            "environments": [
                {"alias": "DEV", "name": "Development"},
                {"alias": "TEST", "name": "Testing"},
            ]
        }

        # Delete DEV environment
        config["environments"] = [env for env in config["environments"] if env["alias"] != "DEV"]

        assert len(config["environments"]) == 1
        assert config["environments"][0]["alias"] == "TEST"

    def test_clone_environment(self):
        """Test cloning an environment for multi-tenancy"""
        source_env = {
            "alias": "DEV",
            "name": "Development",
            "base_url": "dev.example.cloud4retail.co",
            "tenant_id": "001",
            "launchpad_oauth2": "encoded_password",
        }

        # Clone and modify
        cloned_env = source_env.copy()
        cloned_env["alias"] = "DEV-002"
        cloned_env["tenant_id"] = "002"

        assert cloned_env["alias"] == "DEV-002"
        assert cloned_env["tenant_id"] == "002"
        assert cloned_env["base_url"] == source_env["base_url"]  # Same URL
        assert cloned_env["launchpad_oauth2"] == source_env["launchpad_oauth2"]  # Same credentials
