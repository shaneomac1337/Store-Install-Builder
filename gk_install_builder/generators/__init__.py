"""
Generator modules for creating installation scripts and templates
"""

from .template_processor import replace_hostname_regex_powershell, replace_hostname_regex_bash
from .launcher_generator import generate_launcher_templates, create_default_template
from .onboarding_generator import generate_onboarding_script
from .gk_install_generator import generate_gk_install
from .helper_file_generator import (
    generate_store_init_script,
    create_password_files,
    create_component_files,
    create_init_json_files,
    modify_json_files,
    copy_helper_files,
    generate_environments_json
)
from .offline_package_helpers import (
    download_file_thread,
    create_progress_dialog,
    prompt_for_file_selection,
    process_platform_dependency,
    process_component,
    process_onex_ui_package,
    fetch_installer_properties,
    build_installer_preferences
)

__all__ = [
    'replace_hostname_regex_powershell',
    'replace_hostname_regex_bash',
    'generate_launcher_templates',
    'create_default_template',
    'generate_onboarding_script',
    'generate_gk_install',
    'generate_store_init_script',
    'create_password_files',
    'create_component_files',
    'create_init_json_files',
    'modify_json_files',
    'copy_helper_files',
    'generate_environments_json',
    'download_file_thread',
    'create_progress_dialog',
    'prompt_for_file_selection',
    'process_platform_dependency',
    'process_component',
    'process_onex_ui_package',
    'fetch_installer_properties',
    'build_installer_preferences'
]
