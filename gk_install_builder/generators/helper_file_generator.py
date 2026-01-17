"""
Helper file generation functions

This module contains functions for generating various helper files including
store initialization scripts, password files, JSON configuration files, etc.
"""

import os
import json
import base64
import time
import shutil

# Support both package-relative imports (for tests/package use) and direct imports (for running app)
try:
    from ..utils import replace_urls_in_json
except ImportError:
    from utils.helpers import replace_urls_in_json


def generate_store_init_script(output_dir, config, templates_dir):
    """
    Generate store initialization script with platform-specific configuration

    Args:
        output_dir: Directory where the script will be created
        config: Configuration dictionary
        templates_dir: Directory containing template files

    Returns:
        None (writes file to disk)
    """
    platform = config.get("platform", "Windows")

    # Get system types from config
    pos_system_type = config.get("pos_system_type", "GKR-OPOS-CLOUD")
    onex_pos_system_type = config.get("onex_pos_system_type", "GKR-OPOS-ONEX-CLOUD")
    wdm_system_type = config.get("wdm_system_type", "CSE-wdm")
    flow_service_system_type = config.get("flow_service_system_type", "GKR-FLOWSERVICE-CLOUD")
    lpa_service_system_type = config.get("lpa_service_system_type", "CSE-lps-lpa")
    storehub_service_system_type = config.get("storehub_service_system_type", "CSE-sh-cloud")
    rcs_system_type = config.get("rcs_system_type", "GKR-Resource-Cache-Service")
    base_url = config.get("base_url", "test.cse.cloud4retail.co")
    tenant_id = config.get("tenant_id", "001")

    # Get API version from config (default to "new" for 5.27+)
    api_version = config.get("api_version", "new")

    # Define API endpoint mappings for legacy (5.25) vs new (5.27+) APIs
    if api_version == "legacy":
        api_endpoints = {
            "config_structure_search": "/config-service/services/rest/infrastructure/v1/structure/child-nodes/search",
            "config_structure_create": "/config-service/services/rest/infrastructure/v1/structure/create",
            "config_management": "/config-service/services/rest/config-management/v1/parameter-contents/plain",
            "business_unit": f"/swee-sdc/tenants/{tenant_id}/services/rest/master-data/v1/business-units",
            "workstation_base": f"/swee-sdc/tenants/{tenant_id}/services/rest/master-data/v1/workstations",
        }
    else:  # new API (5.27+)
        api_endpoints = {
            "config_structure_search": "/api/config/services/rest/infrastructure/v1/structure/child-nodes/search",
            "config_structure_create": "/api/config/services/rest/infrastructure/v1/structure/create",
            "config_management": "/api/config/services/rest/config-management/v1/parameter-contents/plain",
            "business_unit": "/api/business-unit/rest/v1/business-units",
            "workstation_base": "/api/pos/master-data/rest/v1/workstations",
        }

    # Get version information (same logic as in _generate_gk_install)
    default_version = config.get("version", "v1.0.0")
    use_version_override = config.get("use_version_override", False)
    if use_version_override:
        # Use the storehub version since that's what the store initialization script primarily uses
        version = config.get("storehub_service_version", default_version)
    else:
        version = default_version

    # Copy the appropriate store initialization script based on platform
    if platform == "Windows":
        src_script = os.path.join(templates_dir, "store-initialization.ps1.template")
        dst_script = os.path.join(output_dir, "store-initialization.ps1")
    else:  # Linux
        src_script = os.path.join(templates_dir, "store-initialization.sh.template")
        dst_script = os.path.join(output_dir, "store-initialization.sh")

    # Process the template with variables instead of just copying
    if os.path.exists(src_script):
        with open(src_script, 'r') as f:
            template_content = f.read()

        # Replace template variables
        template_content = template_content.replace("${pos_system_type}", pos_system_type)
        template_content = template_content.replace("${onex_pos_system_type}", onex_pos_system_type)
        template_content = template_content.replace("${wdm_system_type}", wdm_system_type)
        template_content = template_content.replace("${flow_service_system_type}", flow_service_system_type)
        template_content = template_content.replace("${lpa_service_system_type}", lpa_service_system_type)
        template_content = template_content.replace("${storehub_service_system_type}", storehub_service_system_type)
        template_content = template_content.replace("${rcs_system_type}", rcs_system_type)
        template_content = template_content.replace("${base_url}", base_url)
        template_content = template_content.replace("${tenant_id}", tenant_id)

        # Add user_id replacement from configuration
        user_id = config.get("eh_launchpad_username", "1001")
        template_content = template_content.replace("${user_id}", user_id)

        # Add version replacement
        template_content = template_content.replace("@VERSION@", version)

        # Replace API endpoints based on version (legacy vs new)
        # Config-service endpoints
        template_content = template_content.replace(
            "/api/config/services/rest/infrastructure/v1/structure/child-nodes/search",
            api_endpoints["config_structure_search"]
        )
        template_content = template_content.replace(
            "/api/config/services/rest/infrastructure/v1/structure/create",
            api_endpoints["config_structure_create"]
        )
        template_content = template_content.replace(
            "/api/config/services/rest/config-management/v1/parameter-contents/plain",
            api_endpoints["config_management"]
        )
        # Business unit endpoint
        template_content = template_content.replace(
            "/api/business-unit/rest/v1/business-units",
            api_endpoints["business_unit"]
        )
        # Workstation endpoints
        template_content = template_content.replace(
            "/api/pos/master-data/rest/v1/workstations",
            api_endpoints["workstation_base"]
        )

        # Write the processed content to the destination file with Unix line endings
        with open(dst_script, 'w', newline='\n') as f:
            f.write(template_content)

        print(f"  Generated store initialization script with dynamic system types at: {dst_script}")

        # For Linux scripts, make them executable
        if platform == "Linux":
            try:
                os.chmod(dst_script, 0o755)  # rwxr-xr-x
                print(f"  Made {os.path.basename(dst_script)} executable")
            except Exception as e:
                print(f"  Warning: Failed to make {os.path.basename(dst_script)} executable: {e}")


def create_password_files(helper_dir, config):
    """
    Create password files for onboarding

    Args:
        helper_dir: Helper directory where password files will be created
        config: Configuration dictionary with password values

    Returns:
        None (writes files to disk)

    Raises:
        Exception: If password file creation fails
    """
    try:
        # Create tokens directory
        tokens_dir = os.path.join(helper_dir, "tokens")
        os.makedirs(tokens_dir, exist_ok=True)

        # Create basic auth password file (using launchpad_oauth2)
        basic_auth_password = config.get("launchpad_oauth2", "")
        if basic_auth_password:
            encoded_basic = base64.b64encode(basic_auth_password.encode()).decode()
            basic_auth_path = os.path.join(tokens_dir, "basic_auth_password.txt")
            with open(basic_auth_path, 'w') as f:
                f.write(encoded_basic)
            # Create .default backup for factory defaults
            shutil.copy(basic_auth_path, f"{basic_auth_path}.default")

        # Create form password file (using eh_launchpad_password)
        form_password = config.get("eh_launchpad_password", "")
        if form_password:
            encoded_form = base64.b64encode(form_password.encode()).decode()
            form_password_path = os.path.join(tokens_dir, "form_password.txt")
            with open(form_password_path, 'w') as f:
                f.write(encoded_form)
            # Create .default backup for factory defaults
            shutil.copy(form_password_path, f"{form_password_path}.default")

    except Exception as e:
        raise Exception(f"Failed to create password files: {str(e)}")


def create_component_files(helper_dir):
    """
    Create component-specific directories and files

    Args:
        helper_dir: Helper directory where component files will be created

    Returns:
        None (writes files to disk)
    """
    # Create structure directory and files
    structure_dir = os.path.join(helper_dir, "structure")
    os.makedirs(structure_dir, exist_ok=True)
    print(f"  Created directory: {structure_dir}")

    # Create create_structure.json template for all components
    create_structure_json = '''{
    "tenant": {
        "tenantId": "@TENANT_ID@"
    },
    "store": {
        "retailStoreId": "@RETAIL_STORE_ID@"
    },
    "station": {
        "systemName": "@SYSTEM_TYPE@",
        "workstationId": "@WORKSTATION_ID@",
        "name": "@STATION_NAME@"
    },
    "user": "@USER_ID@"
}'''

    # Write create_structure.json file
    file_path = os.path.join(structure_dir, "create_structure.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(create_structure_json)
    print(f"  Created structure template: {file_path}")


def create_init_json_files(helper_dir, config):
    """
    Create init JSON files for store configuration

    Args:
        helper_dir: Helper directory where init JSON files will be created
        config: Configuration dictionary

    Returns:
        None (writes files to disk)
    """
    init_dir = os.path.join(helper_dir, "init")
    os.makedirs(init_dir, exist_ok=True)

    # Get tenant_id from config
    tenant_id = config.get("tenant_id", "001")

    # Create get_store.json template with placeholder for retailStoreId
    store_json_content = '''{
  "station": {
    "systemName": "GKR-Store",
    "tenantId": "''' + tenant_id + '''",
    "retailStoreId": "@RETAIL_STORE_ID@"
  }
}'''

    # Write get_store.json file
    file_path = os.path.join(init_dir, "get_store.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(store_json_content)
    print(f"  Created init JSON file: {file_path}")

    # Create component-specific directories
    storehub_dir = os.path.join(init_dir, "storehub")
    os.makedirs(storehub_dir, exist_ok=True)

    # Get launcher settings for StoreHub
    storehub_settings = {}
    storehub_launcher_settings_key = "storehub_service_launcher_settings"

    if storehub_launcher_settings_key in config:
        storehub_settings = config[storehub_launcher_settings_key]

    # Get default values or values from launcher settings
    jms_port = storehub_settings.get("applicationJmsPort", "7001")
    firebird_port = storehub_settings.get("firebirdServerPort", "3050")
    firebird_user = storehub_settings.get("firebirdServerUser", "SYSDBA")
    firebird_password = storehub_settings.get("firebirdServerPassword", "masterkey")
    https_port = storehub_settings.get("applicationServerHttpsPort", "8543")

    # Get system name from config
    system_name = config.get("storehub_service_system_type", "CSE-sh-cloud")

    # Get version from config
    version = "v1.1.0"  # Default version
    if config.get("use_version_override", False):
        version = config.get("storehub_service_version", "v1.1.0")
    else:
        version = config.get("version", "v1.1.0")

    # Get the username from config - with debug print
    username = config.get("eh_launchpad_username")
    print(f"Using eh_launchpad_username for StoreHub config: {username}")

    # Create update_config.json template with values from launcher settings
    update_config_json_content = '''{
  "levelDescriptor": {
    "structureUniqueName": "@STRUCTURE_UNIQUE_NAME@"
  },
  "systemDescriptor": {
    "systemName": "''' + system_name + '''",
    "systemVersionList": [
      {
        "name": "@SYSTEM_VERSION@"
      }
    ]
  },
  "user": "''' + username + '''",
  "parameterValueChangeList": [
    {
      "name": "activemq.properties",
      "url": "jms-engine.port",
      "value": "''' + jms_port + '''"
    },
    {
      "name": "ds-embedded.properties",
      "url": "datasource.port",
      "value": "''' + firebird_port + '''"
    },
    {
      "name": "ds-embedded.properties",
      "url": "datasource.username",
      "value": "''' + firebird_user + '''"
    },
    {
      "name": "secret.properties",
      "url": "ds-embedded.datasource.password_encrypted",
      "value": "''' + firebird_password + '''"
    },
    {
      "name": "data-router-adapter.properties",
      "url": "swee.common.data-router.adapter.message-adapter.host",
      "value": "@HOSTNAME@"
    },
    {
      "name": "data-router-adapter.properties",
      "url": "swee.common.data-router.adapter.message-adapter.http.port",
      "value": "''' + https_port + '''"
    }
  ]
}'''

    # Write update_config.json file for StoreHub
    file_path = os.path.join(storehub_dir, "update_config.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(update_config_json_content)
    print(f"  Created StoreHub config file: {file_path}")

    # Create RCS directory and config
    rcs_dir = os.path.join(init_dir, "rcs")
    os.makedirs(rcs_dir, exist_ok=True)

    # Get RCS system name from config
    rcs_system_name = config.get("rcs_system_type", "GKR-Resource-Cache-Service")

    # Get RCS version from config
    rcs_version = "v1.0.0"  # Default version
    if config.get("use_version_override", False):
        rcs_version = config.get("rcs_version", "v1.0.0")
    else:
        rcs_version = config.get("rcs_version", "v1.0.0")

    # Create update_config.json template for RCS
    rcs_update_config_json_content = '''{
  "levelDescriptor": {
    "structureUniqueName": "@STRUCTURE_UNIQUE_NAME@"
  },
  "systemDescriptor": {
    "systemName": "''' + rcs_system_name + '''",
    "systemVersionList": [
      {
        "name": "@SYSTEM_VERSION@"
      }
    ]
  },
  "user": "''' + (username if username else "@EH_LAUNCHPAD_USERNAME@") + '''",
  "parameterValueChangeList": [
    {
      "name": "system.properties",
      "url": "rcs.url",
      "value": "@RCS_URL@"
    }
  ]
}'''

    # Write update_config.json file for RCS
    rcs_file_path = os.path.join(rcs_dir, "update_config.json")
    with open(rcs_file_path, 'w', encoding='utf-8') as f:
        f.write(rcs_update_config_json_content)
    print(f"  Created RCS config file: {rcs_file_path}")


def modify_json_files(helper_dir, config, replace_urls_in_json_func):
    """
    Modify JSON files with new configuration

    Args:
        helper_dir: Helper directory containing JSON files to modify
        config: Configuration dictionary
        replace_urls_in_json_func: Function to replace URLs in JSON structures

    Returns:
        None (modifies files in place)
    """
    try:
        tenant_id = config.get("tenant_id", "001")
        username = config.get("eh_launchpad_username", "1001")
        base_url = config.get("base_url", "")

        # 1. Modify all JSON files in onboarding directory
        onboarding_dir = os.path.join(helper_dir, "onboarding")
        if os.path.exists(onboarding_dir):
            json_files = [f for f in os.listdir(onboarding_dir) if f.endswith('.json')]

            for json_file in json_files:
                file_path = os.path.join(onboarding_dir, json_file)
                try:
                    with open(file_path, 'r') as f:
                        data = json.loads(f.read())

                    # Recursively replace URLs in the JSON structure
                    replace_urls_in_json_func(data, base_url)

                    # Update tenant_id if present
                    if "tenant_id" in data:
                        data["tenant_id"] = tenant_id
                    if "tenantId" in data:
                        data["tenantId"] = tenant_id
                    if "restrictions" in data and "tenantId" in data["restrictions"]:
                        data["restrictions"]["tenantId"] = tenant_id

                    # Write updated JSON with proper formatting
                    with open(file_path, 'w') as f:
                        json.dump(data, f, indent=4)
                    print(f"  Modified onboarding file: {json_file}")

                except Exception as e:
                    print(f"  Warning: Failed to modify {json_file}: {str(e)}")

        # 2. Modify JSON files in init directory
        init_dir = os.path.join(helper_dir, "init")
        if os.path.exists(init_dir):
            # Update get_store.json
            get_store_path = os.path.join(init_dir, "get_store.json")
            if os.path.exists(get_store_path):
                try:
                    with open(get_store_path, 'r') as f:
                        data = json.loads(f.read())

                    # Update tenantId in station object
                    if "station" in data and "tenantId" in data["station"]:
                        data["station"]["tenantId"] = tenant_id

                    with open(get_store_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"  Modified init file: get_store.json")
                except Exception as e:
                    print(f"  Warning: Failed to modify get_store.json: {str(e)}")

            # Update storehub/update_config.json
            storehub_config_path = os.path.join(init_dir, "storehub", "update_config.json")
            if os.path.exists(storehub_config_path):
                try:
                    with open(storehub_config_path, 'r') as f:
                        data = json.loads(f.read())

                    # Update user field
                    if "user" in data:
                        data["user"] = username

                    with open(storehub_config_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"  Modified storehub file: update_config.json")
                except Exception as e:
                    print(f"  Warning: Failed to modify update_config.json: {str(e)}")

            # Update rcs/update_config.json
            rcs_config_path = os.path.join(init_dir, "rcs", "update_config.json")
            if os.path.exists(rcs_config_path):
                try:
                    with open(rcs_config_path, 'r') as f:
                        data = json.loads(f.read())

                    # Update user field
                    if "user" in data:
                        data["user"] = username

                    with open(rcs_config_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"  Modified rcs file: update_config.json")
                except Exception as e:
                    print(f"  Warning: Failed to modify rcs update_config.json: {str(e)}")

        # 3. Modify JSON files in structure directory
        structure_dir = os.path.join(helper_dir, "structure")
        if os.path.exists(structure_dir):
            # Update create_structure.json
            create_structure_path = os.path.join(structure_dir, "create_structure.json")
            if os.path.exists(create_structure_path):
                try:
                    with open(create_structure_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Replace placeholders
                    content = content.replace("@TENANT_ID@", tenant_id)
                    # Note: Other placeholders like @RETAIL_STORE_ID@, @SYSTEM_TYPE@, @WORKSTATION_ID@,
                    # @STATION_NAME@, @USER_ID@ are replaced at runtime by the installation scripts

                    with open(create_structure_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"  Modified structure file: create_structure.json (tenant_id={tenant_id})")
                except Exception as e:
                    print(f"  Warning: Failed to modify create_structure.json: {str(e)}")

    except Exception as e:
        print(f"  Warning: Error modifying JSON files: {str(e)}")


def copy_helper_files(output_dir, config, script_dir, helper_structure, launcher_templates):
    """
    Copy helper files to output directory

    Args:
        output_dir: Output directory path
        config: Configuration dictionary
        script_dir: Script directory path (where generator.py is located)
        helper_structure: Helper directory structure dictionary
        launcher_templates: Launcher templates dictionary

    Returns:
        None (copies files and creates directories)
    """
    import shutil

    try:
        # Use absolute paths for source and destination
        helper_src = os.path.join(script_dir, 'helper')
        helper_dst = os.path.join(output_dir, 'helper')

        print(f"Copying helper files:")
        print(f"  Source: {helper_src}")
        print(f"  Destination: {helper_dst}")

        # Generate store initialization script from templates
        templates_dir = os.path.join(script_dir, 'templates')
        generate_store_init_script(output_dir, config, templates_dir)

        # Check if source directory exists
        if not os.path.exists(helper_src):
            # Try to find helper directory in parent directory
            parent_helper = os.path.join(os.path.dirname(script_dir), 'helper')
            if os.path.exists(parent_helper):
                helper_src = parent_helper
                print(f"  Found helper directory in parent: {helper_src}")
            else:
                # Create the required directory structure instead of failing
                print(f"  Helper directory not found. Creating necessary directory structure.")
                from ..utils.helpers import create_helper_structure
                create_helper_structure(helper_dst, helper_structure, lambda h: create_component_files(h))

                # Create password files
                create_password_files(helper_dst, config)

                # Create init JSON files
                create_init_json_files(helper_dst, config)

                # Create component-specific files (like create_structure.json)
                create_component_files(helper_dst)

                # Create launchers directory
                launchers_dir = os.path.join(helper_dst, 'launchers')
                os.makedirs(launchers_dir, exist_ok=True)

                # Generate launcher templates with custom settings
                from .launcher_generator import generate_launcher_templates
                generate_launcher_templates(launchers_dir, config, launcher_templates)

                # Modify JSON files with the correct URLs and tenant_id
                modify_json_files(helper_dst, config, replace_urls_in_json)

                print(f"Successfully created helper files at {helper_dst}")
                return

        # Create helper directory if it doesn't exist
        if not os.path.exists(helper_dst):
            os.makedirs(helper_dst, exist_ok=True)

        # Ensure all required directories exist in the destination
        for dir_name in helper_structure.keys():
            os.makedirs(os.path.join(helper_dst, dir_name), exist_ok=True)

        # Copy helper directory structure, excluding launchers directory
        for item in os.listdir(helper_src):
            src_item = os.path.join(helper_src, item)
            dst_item = os.path.join(helper_dst, item)

            if item == 'launchers':
                # Skip launchers directory, we'll handle it separately
                continue

            if os.path.isdir(src_item):
                # Create directory if it doesn't exist
                os.makedirs(dst_item, exist_ok=True)

                # Copy directory contents
                for subitem in os.listdir(src_item):
                    src_subitem = os.path.join(src_item, subitem)
                    dst_subitem = os.path.join(dst_item, subitem)
                    if os.path.isdir(src_subitem):
                        if os.path.exists(dst_subitem):
                            shutil.rmtree(dst_subitem)
                        shutil.copytree(src_subitem, dst_subitem)
                    else:
                        shutil.copy2(src_subitem, dst_subitem)
            else:
                # Copy file
                shutil.copy2(src_item, dst_item)

        # Create launchers directory
        launchers_dir = os.path.join(helper_dst, 'launchers')
        os.makedirs(launchers_dir, exist_ok=True)

        # Generate launcher templates with custom settings
        from .launcher_generator import generate_launcher_templates
        generate_launcher_templates(launchers_dir, config, launcher_templates)

        # Create password files
        create_password_files(helper_dst, config)

        # Create init JSON files
        create_init_json_files(helper_dst, config)

        # Create component-specific files (like create_structure.json)
        create_component_files(helper_dst)

        # Modify JSON files with the correct URLs and tenant_id
        modify_json_files(helper_dst, config, replace_urls_in_json)

        print(f"Successfully copied helper files to {helper_dst}")

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error copying helper files: {error_details}")
        raise Exception(f"Failed to copy helper files: {str(e)}")


def generate_environments_json(output_dir, config):
    """
    Generate environments.json file for multi-environment support

    Args:
        output_dir: Output directory path
        config: Configuration dictionary containing environments list

    Returns:
        None (writes environments.json file)
    """
    try:
        environments = config.get("environments", [])

        # Create helper/environments directory
        env_dir = os.path.join(output_dir, "helper", "environments")
        os.makedirs(env_dir, exist_ok=True)

        if not environments:
            print("No environments configured, generating empty environments.json")
            # Write empty array wrapped in object
            env_json_path = os.path.join(env_dir, "environments.json")
            with open(env_json_path, 'w') as f:
                json.dump({"environments": []}, f, indent=2)
            print(f"Generated empty environments.json at: {env_json_path}")
            return

        print(f"\nGenerating environments.json with {len(environments)} environment(s)...")

        # Prepare environments data with base64-encoded passwords
        processed_envs = []
        for env in environments:
            processed_env = {
                "alias": env.get("alias", ""),
                "name": env.get("name", ""),
                "base_url": env.get("base_url", ""),
                "tenant_id": env.get("tenant_id", config.get("tenant_id", "001")) if not env.get("use_default_tenant", False) else config.get("tenant_id", "001"),
                "use_default_tenant": env.get("use_default_tenant", False)
            }

            # Base64 encode passwords for basic security
            oauth_password = env.get("launchpad_oauth2", "")
            if oauth_password:
                processed_env["launchpad_oauth2_b64"] = base64.b64encode(oauth_password.encode()).decode()

            eh_username = env.get("eh_launchpad_username", "")
            if eh_username:
                processed_env["eh_launchpad_username"] = eh_username

            eh_password = env.get("eh_launchpad_password", "")
            if eh_password:
                processed_env["eh_launchpad_password_b64"] = base64.b64encode(eh_password.encode()).decode()

            processed_envs.append(processed_env)
            print(f"  - {env.get('alias')}: {env.get('name')} ({env.get('base_url')})")

        # Write environments.json wrapped in object
        env_json_path = os.path.join(env_dir, "environments.json")
        with open(env_json_path, 'w') as f:
            json.dump({"environments": processed_envs}, f, indent=2)

        print(f"Generated environments.json at: {env_json_path}")

    except Exception as e:
        print(f"Warning: Failed to generate environments.json: {str(e)}")
        import traceback
        print(f"Error details: {traceback.format_exc()}")
