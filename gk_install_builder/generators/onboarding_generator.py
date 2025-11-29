"""
Onboarding script generation functions

This module contains functions for generating onboarding scripts
with platform-specific configurations.
"""

import os


def generate_onboarding_script(output_dir, config, templates_dir):
    """
    Generate onboarding script with replaced values based on platform

    Args:
        output_dir: Directory where the onboarding script will be created
        config: Configuration dictionary with platform and settings
        templates_dir: Directory containing onboarding templates

    Returns:
        None (writes file to disk)

    Raises:
        Exception: If template file not found or generation fails
    """
    try:
        # Get platform from config (default to Windows if not specified)
        platform = config.get("platform", "Windows")

        # Determine template and output paths based on platform
        if platform == "Windows":
            template_filename = "onboarding.ps1.template"
            output_filename = "onboarding.ps1"
        else:  # Linux
            template_filename = "onboarding.sh.template"
            output_filename = "onboarding.sh"

        # Use absolute paths for template and output
        template_path = os.path.join(templates_dir, template_filename)
        output_path = os.path.join(output_dir, output_filename)

        print(f"Generating {output_filename}:")
        print(f"  Template path: {template_path}")
        print(f"  Output path: {output_path}")

        # Check if template exists
        if not os.path.exists(template_path):
            raise Exception(f"Template file not found: {template_path}")

        with open(template_path, 'r') as f:
            content = f.read()

        # Get configuration values
        base_url = config.get("base_url", "test.cse.cloud4retail.co")
        username = config.get("username", "launchpad")
        form_username = config.get("eh_launchpad_username", "1001")
        tenant_id = config.get("tenant_id", "001")

        # Get API version from config (default to "new" for 5.27+)
        api_version = config.get("api_version", "new")

        # Define onboarding API endpoint based on version
        if api_version == "legacy":
            onboarding_api = "/cims/services/rest/cims/v1/onboarding/tokens"
        else:
            onboarding_api = "/api/iam/cim/rest/v1/onboarding/tokens"

        # Replace API endpoint based on version (common for both platforms)
        content = content.replace(
            '/api/iam/cim/rest/v1/onboarding/tokens',
            onboarding_api
        )

        # Replace configurations based on platform
        if platform == "Windows":
            # Windows-specific replacements
            content = content.replace(
                'test.cse.cloud4retail.co',
                base_url
            )
            content = content.replace(
                '$username = "launchpad"',
                f'$username = "{username}"'
            )
            content = content.replace(
                '@FORM_USERNAME@',
                form_username
            )
            content = content.replace(
                '[string]$tenant_id = "001"',
                f'[string]$tenant_id = "{tenant_id}"'
            )
        else:  # Linux
            # Linux-specific replacements
            content = content.replace(
                'base_url="test.cse.cloud4retail.co"',
                f'base_url="{base_url}"'
            )
            content = content.replace(
                'tenant_id="001"',
                f'tenant_id="{tenant_id}"'
            )
            content = content.replace(
                'username="launchpad"',
                f'username="{username}"'
            )
            content = content.replace(
                '@FORM_USERNAME@',
                form_username
            )

        # Write the modified content
        with open(output_path, 'w', newline='\n') as f:
            f.write(content)

        # For Linux scripts, make the file executable
        if platform == "Linux":
            try:
                os.chmod(output_path, 0o755)  # rwxr-xr-x
                print(f"Made {output_filename} executable")
            except Exception as e:
                print(f"Warning: Failed to make {output_filename} executable: {e}")

        print(f"Successfully generated {output_filename} at {output_path}")

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error generating onboarding script: {error_details}")
        raise Exception(f"Failed to generate onboarding script: {str(e)}")
