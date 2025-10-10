# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

GK Install Builder is a Python GUI application for generating installation packages for retail store environments. It creates platform-specific installation scripts (Windows PowerShell and Linux Bash), configuration files, and deployment packages for multiple retail components (POS, WDM, Flow Service, LPA Service, StoreHub Service).

**Key Technology**: CustomTkinter-based GUI application that generates installation scripts and integrates with WebDAV and Pleasant Password Server.

## Development Setup

### Prerequisites
- Python 3.7 or higher (currently using Python 3.13.5)
- Dependencies: customtkinter, requests, webdavclient3, urllib3, pillow, setuptools, wheel, pyinstaller

### Installation
```pwsh
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m gk_install_builder.main
```

### Building Executable
```pwsh
# Create standalone executable (uses StoreInstallBuilder.spec)
pyinstaller StoreInstallBuilder.spec
```

The executable and dependencies will be in `dist/GK Install Builder/` directory.

## Core Architecture

### Main Components

1. **Main Application (`gk_install_builder/main.py`)**: GUI controller with CustomTkinter interface
   - Wizard-style interface for first-time users
   - Multi-section configuration form with auto-save
   - Custom mousewheel scrolling for cross-platform support (Linux Button-4/5, Windows/macOS MouseWheel)
   - Integration with Pleasant Password Server browser
   - WebDAV browser for remote file selection

2. **Project Generator (`gk_install_builder/generator.py`)**: Generates installation packages
   - Template-based script generation using string substitution
   - WebDAV integration via `WebDAVBrowser` class
   - Creates complete directory structure with helper files
   - Supports both Windows (.ps1) and Linux (.sh) scripts

3. **Config Manager (`gk_install_builder/config.py`)**: Configuration persistence
   - JSON-based configuration storage (`gk_install_config.json`)
   - Auto-save with debounce logic (1 second delay)
   - Entry widget registration for automatic binding
   - Platform-specific default paths

4. **Detection Manager (`gk_install_builder/detection.py`)**: Store/workstation ID detection
   - Hostname-based detection with customizable regex patterns
   - File-based detection using station files
   - Platform-specific regex patterns for Windows/Linux

5. **Pleasant Password Client (`gk_install_builder/pleasant_password_client.py`)**: KeePass integration
   - OAuth2 authentication
   - Folder and credential browsing
   - Password retrieval for automated configuration

### Generated Output Structure

The generator creates the following structure:
```
output_dir/
├── GKInstall.ps1 / GKInstall.sh      # Main installation script
├── onboarding.ps1 / onboarding.sh     # Initial setup script
├── store-initialization.ps1 / .sh     # Store-specific setup
├── certificate.p12                     # SSL certificate (if provided)
└── helper/
    ├── launchers/                      # Component launcher templates
    │   ├── launcher.pos.template
    │   ├── launcher.wdm.template
    │   ├── launcher.flow-service.template
    │   ├── launcher.lpa-service.template
    │   └── launcher.storehub-service.template
    ├── onboarding/                     # Component onboarding configs
    │   ├── pos.onboarding.json
    │   ├── wdm.onboarding.json
    │   ├── flow-service.onboarding.json
    │   ├── lpa-service.onboarding.json
    │   └── storehub-service.onboarding.json
    ├── tokens/                         # Authentication tokens
    │   ├── access_token.txt
    │   ├── basic_auth_password.txt
    │   └── form_password.txt
    ├── init/                           # Initialization configs
    │   └── get_store.json
    ├── storehub/                       # StoreHub-specific configs
    │   └── update_config.json
    └── structure/                      # Directory structure config
        └── create_structure.json
```

## Template System

Templates are located in `gk_install_builder/templates/`:
- `GKInstall.ps1.template` / `GKInstall.sh.template` - Main installation scripts
- `onboarding.ps1.template` / `onboarding.sh.template` - Onboarding scripts
- `store-initialization.ps1.template` / `store-initialization.sh.template` - Store initialization

Templates use `@VARIABLE@` syntax for substitution. The generator replaces these placeholders with actual configuration values using string replacement.

### Key Template Variables
- `@BASE_URL@` - Base URL for the cloud environment
- `@TENANT_ID@` - Tenant identifier
- `@SYSTEM_TYPE@` - Component system type (e.g., GKR-POS-CLOUD)
- `@SSL_PASSWORD@` - Certificate password
- `@USE_DEFAULT_VERSIONS@` - Flag for version management
- `@AUTH_SERVICE_BA_USER@` / `@AUTH_SERVICE_BA_PASSWORD@` - Auth credentials
- Platform-specific paths for Firebird, Jaybird, etc.

## Configuration

### Configuration File
Application state is persisted to `gk_install_config.json` in the project root. This includes:
- Project metadata (name, base URL, version)
- Platform selection (Windows/Linux)
- Component-specific versions and settings
- Detection configuration
- Security credentials
- WebDAV credentials

### Version Management
Default component versions are defined in `gk_install_builder/default_versions.json` (fallback for Employee Hub Service API). The application can:
1. Fetch versions dynamically from Employee Hub Service API (if token available)
2. Use override versions specified in the UI
3. Fall back to default versions from JSON file

## Important Patterns

### Threading for Blocking Operations
Long-running operations (WebDAV, file operations, API calls) use threading to keep GUI responsive:
```python
import threading
thread = threading.Thread(target=blocking_operation, daemon=True)
thread.start()
```

### Platform-Specific Handling
Many operations have platform-specific logic:
- Path separators (Windows backslash vs. Unix forward slash)
- Default installation paths (`C:\gkretail` vs. `/usr/local/gkretail`)
- Hostname detection regex patterns
- Mousewheel events (Button-4/5 for Linux, MouseWheel for Windows/macOS)

### WebDAV Integration
WebDAV operations use the `WebDAVBrowser` class with certificate verification disabled:
- SSL warnings are suppressed
- Basic authentication with username/password
- Path normalization for cross-platform compatibility

### Entry Widget Management
The ConfigManager tracks all entry widgets for auto-save:
```python
config_manager.register_entry(key, entry_widget, fixed_value=None)
config_manager.update_entry_value(key, new_value)  # Updates widget and config
```

## Testing

### Manual Testing
Use `test_api_call.ps1` to test Employee Hub Service API connectivity:
```pwsh
.\test_api_call.ps1 -base_url "example.cloud4retail.co" -tenant_id "001"
```

This script tests:
- Token file existence and validity
- API connectivity
- Token generation process
- Version property retrieval

### Test Data
`test.cases` file contains test scenarios (format not standardized - check file for specific cases).

## Code Style Guidelines

From `.cursorrules`:
- Write concise, technical responses with accurate Python examples
- Follow PEP 8 style guidelines
- Use classes for major components; prefer composition over inheritance
- Use docstrings and inline comments for clarity
- Avoid global state; manage via class instances
- Use threading for blocking operations
- Store configuration in JSON with auto-save debounce logic
- Provide tooltips and clear error dialogs for user guidance

## Platform-Specific Notes

### Windows
- Default base directory: `C:\gkretail`
- Firebird path: `C:\Program Files\Firebird\Firebird_3_0`
- Jaybird path: `C:\gkretail\Jaybird`
- Uses PowerShell scripts (`.ps1`)

### Linux
- Default base directory: `/usr/local/gkretail`
- Firebird path: `/opt/firebird`
- Jaybird path: `/usr/local/gkretail/Jaybird`
- Uses Bash scripts (`.sh`)
- Requires special mousewheel handling (Button-4/Button-5 events)

## Integration Points

### Pleasant Password Server
OAuth2-based authentication flow:
1. Get OAuth token from `/OAuth2/Token` endpoint
2. Use bearer token for API calls
3. Browse folder hierarchy
4. Retrieve credential passwords by entry ID

### WebDAV Server
Connection details:
- Base URL pattern: `https://BASE_URL/dsg/webdav`
- Authentication: Basic Auth
- SSL verification disabled
- Used for browsing and selecting remote files/certificates

### Employee Hub Service API
Endpoint: `https://BASE_URL/employee-hub-service/services/rest/v1/properties`
- Requires bearer token (from onboarding process)
- Query params: `scope=FP&referenceId=platform` (modified versions) or `scope=FPD&referenceId=platform` (default versions)
- Returns component version properties
- Headers: `authorization: Bearer TOKEN`, `gk-tenant-id: TENANT_ID`

## Common Development Tasks

### Adding a New Component
1. Add component entry to `helper_structure` in `generator.py`
2. Create launcher template in `helper/launchers/`
3. Create onboarding config in `helper/onboarding/`
4. Add detection config in `detection.py` `custom_filenames` dict
5. Update UI in `main.py` to include new component section
6. Add version property mapping in default_versions.json

### Modifying Generated Scripts
1. Edit template files in `gk_install_builder/templates/`
2. Ensure all `@VARIABLE@` placeholders are defined in generator substitution
3. Test both Windows and Linux templates
4. Update both main scripts and onboarding/initialization scripts if needed

### Adjusting Configuration Defaults
1. Modify `_get_default_config()` in `config.py`
2. Consider platform-specific defaults
3. Update UI default values in `main.py` if needed
4. Test with fresh configuration (delete `gk_install_config.json`)

## Notes

- The application automatically indexes new codebases when entering git repositories
- Generated scripts include automatic version detection from package filenames
- Templates use token-based replacement (not advanced templating engines)
- Configuration auto-saves after 1-second delay to reduce file I/O
- WebDAV operations bypass SSL certificate validation (internal use)
