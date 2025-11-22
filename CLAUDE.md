# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**GK Install Builder** is a Python GUI application that generates cross-platform installation packages for retail store environments. It creates platform-specific installation scripts (Windows PowerShell and Linux Bash), configuration files, and deployment packages for retail components (POS, WDM, Flow Service, LPA Service, StoreHub Service).

**Current Branch**: `refactor` (main development branch is `main`)

**Recent Major Refactoring (November 2025)**: The codebase underwent a comprehensive refactoring that reduced `generator.py` from 3,592 lines to 899 lines (75.0% reduction) while maintaining 100% test coverage (143/143 tests passing). All functionality has been preserved with zero regressions.

## Development Commands

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Run development instance
python -m gk_install_builder.main

# Build standalone Windows executable
pyinstaller StoreInstallBuilder.spec
# Output: dist/GK Install Builder/GK Install Builder.exe
```

### Testing
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run test suite
pytest tests/

# Run with coverage
pytest --cov=gk_install_builder tests/

# Run specific test file
pytest tests/unit/test_config_management.py
```

## Core Architecture

### Main Components

1. **Main Application** (`gk_install_builder/main.py` - ~1,392 lines)
   - CustomTkinter-based GUI with wizard interface for first-time users
   - Multi-section configuration form with auto-save (1-second debounce)
   - Integration manager for all feature modules

2. **Project Generator** (`gk_install_builder/generator.py` - 899 lines, refactored)
   - Main orchestrator for installation package generation
   - Coordinates all generation modules and manages the overall build process
   - Creates complete directory structure with helper files
   - Delegates to specialized generator modules for specific tasks
   - Includes `DSGRestBrowser` class for REST API integration with token refresh on 401 errors

3. **Generator Modules** (`gk_install_builder/generators/` - NEW)
   - **`gk_install_generator.py`** (771 lines): GKInstall script generation with template variable replacement, hostname/file detection code injection, and platform-specific regex handling
   - **`helper_file_generator.py`**: Helper file operations, store initialization scripts, component files, JSON configs, and multi-environment support
   - **`launcher_generator.py`**: Component launcher template generation with per-component settings
   - **`onboarding_generator.py`**: Onboarding script generation for both platforms
   - **`template_processor.py`**: Hostname regex replacement and template token processing
   - **`offline_package_helpers.py`**: File download threading, progress tracking, and package handling

4. **Config Manager** (`gk_install_builder/config.py` - 359 lines)
   - JSON-based configuration storage (`gk_install_config.json`)
   - Auto-save with 1-second debounce to reduce file I/O
   - Entry widget registration for automatic two-way data binding
   - Platform-specific default paths (Windows: `C:\gkretail`, Linux: `/usr/local/gkretail`)

5. **Detection Manager** (`gk_install_builder/detection.py` - 393 lines)
   - Store/Workstation ID detection via hostname patterns or station files
   - **Detection Priority** (in generated scripts):
     - **Priority 0**: CLI parameters (`--storeId`, `--workstationId`) - highest priority
     - **Priority 1**: Update mode (read from existing station.properties)
     - **Priority 2**: Hostname detection (regex patterns)
     - **Priority 3**: File detection (.station files)
     - **Priority 4**: Manual input (user prompts)
   - Supports 2-group patterns (`STORE-101`) and 3-group patterns (`ENV-STORE-101`) for environment detection

6. **Environment Manager** (`gk_install_builder/environment_manager.py` - 492 lines)
   - Multi-tenancy support (DEV, QA, PROD environments)
   - Per-environment credentials and base URLs
   - Environment aliasing and cloning

7. **Generator Configuration** (`gk_install_builder/gen_config/generator_config.py` - 156 lines)
   - Generator configuration management
   - Centralized configuration for generation processes
   - Configuration validation and defaults

### Utility Modules (`gk_install_builder/utils/` - EXPANDED)

- **helpers.py**: JSON processing utilities
- **tooltips.py**: UI tooltip helpers
- **ui_colors.py**: Consistent color scheme
- **version.py**: Version management utilities (NEW)
- **environment_setup.py** (42 lines): Environment setup utilities
- **file_operations.py** (128 lines): File operation utilities

### Feature Modules (`gk_install_builder/features/`)

- **auto_fill.py**: Auto-populate fields from base URL (extracts project code, detects system types)
- **certificate_manager.py**: SSL certificate import/generation with password protection
- **platform_handler.py**: Windows/Linux platform switching with platform-specific defaults
- **version_manager.py**: Component version management with multiple sources (API, Config-Service, defaults)

### Integration Modules (`gk_install_builder/integrations/`)

- **api_client.py**: OAuth2 token generation and comprehensive API testing
  - Function Pack API testing (all 5 components with FP/FPD scope fallback)
  - Config-Service API testing (all 5 components with version lists)
  - Detailed [TEST API], [CONFIG API], and [TOKEN GEN] logging
- **keepass_handler.py**: Pleasant Password Server integration for credential retrieval

### Dialog Modules (`gk_install_builder/dialogs/`)

- **detection_settings.py**: Store/Workstation detection configuration
- **launcher_settings.py**: Component launcher editor
- **offline_package.py**: Offline package creator for internet-free environments
- **download_dialogs.py** (248 lines): Download progress dialogs
- **about.py**: About dialog

## Template System

### Location
Templates are in `gk_install_builder/templates/`:
- `GKInstall.ps1.template` / `GKInstall.sh.template` - Main installation scripts
- `onboarding.ps1.template` / `onboarding.sh.template` - Initial setup scripts
- `store-initialization.ps1.template` / `store-initialization.sh.template` - Store-specific configuration

### Template Syntax
Uses `@VARIABLE@` token replacement (simple string substitution, no templating engine).

**Key Variables**:
- `@BASE_URL@` - Cloud environment URL
- `@TENANT_ID@` - Tenant identifier
- `@SYSTEM_TYPE@` - Component type (e.g., GKR-POS-CLOUD)
- `@SSL_PASSWORD@` - Certificate password
- `@AUTH_SERVICE_BA_USER@` / `@AUTH_SERVICE_BA_PASSWORD@` - Auth credentials
- `@BASE_INSTALL_DIR@` - Installation directory
- `@FIREBIRD_SERVER_PATH@` - Firebird database path
- `@USE_DEFAULT_VERSIONS@` - Version management flag

## Generated Output Structure

The generator creates this structure in the output directory:

```
output_dir/
├── GKInstall.ps1 / GKInstall.sh           # Main installer
├── onboarding.ps1 / onboarding.sh          # Initial setup
├── store-initialization.ps1 / .sh          # Store-specific config
├── certificate.p12                          # SSL certificate (if provided)
└── helper/
    ├── launchers/                           # Component launcher templates
    ├── onboarding/                          # Component onboarding configs (JSON)
    ├── tokens/                              # Authentication token files
    ├── init/                                # Initialization configs
    ├── storehub/                            # StoreHub-specific configs
    └── structure/                           # Directory structure configs
```

## Important Architectural Patterns

### Configuration Auto-Save with Debounce
The ConfigManager uses a 1-second debounce to batch saves and reduce file I/O:
```python
config_manager.register_entry(key, entry_widget, fixed_value=None)
config_manager.update_entry_value(key, new_value)  # Updates widget and config
```

### Detection Priority System
Generated scripts implement a multi-tier detection system with CLI parameters having the highest priority. This ensures that installation scripts can be automated while still supporting manual installation flows.

### Platform-Specific Handling
Many operations have platform-specific logic:
- Path separators (Windows `\` vs Unix `/`)
- Default installation paths
- Hostname detection regex patterns
- Mousewheel events (Button-4/5 for Linux, MouseWheel for Windows/macOS)

### Threading for Responsive GUI
All blocking operations (WebDAV, file operations, API calls) use threading:
```python
import threading
thread = threading.Thread(target=blocking_operation, daemon=True)
thread.start()
```

## Key Integration Points

### Pleasant Password Server
OAuth2-based KeePass integration:
1. Authenticate via `/OAuth2/Token` endpoint
2. Browse folder hierarchy
3. Retrieve credentials by entry ID
4. Session-level credential caching (class variables in main.py)

### Employee Hub Service API
Endpoint: `https://BASE_URL/employee-hub-service/services/rest/v1/properties`
- Requires OAuth2 bearer token and `gk-tenant-id` header
- Query params: `scope=FP&referenceId=platform` (modified versions) or `scope=FPD&referenceId=platform` (defaults)
- Returns component version properties

### Config-Service API
Alternative version retrieval method (newer approach).

### REST API Integration (DSGRestBrowser)
Used in generator.py for file browsing:
- Automatic token refresh on 401 errors
- Retry logic with new tokens
- File/directory browsing capabilities

## Code Style Guidelines (from .cursorrules)

- Use CustomTkinter for all GUI elements; leverage scrollable frames and tooltips
- Structure application as wizard for first-time users
- Use classes for major components; prefer composition over inheritance
- Follow PEP 8 style guidelines
- Use docstrings and inline comments for clarity
- Avoid global state; manage via class instances
- Store configuration in JSON with auto-save debounce logic
- Use threading for blocking operations
- Handle missing files, invalid input, and external errors gracefully
- Integrate securely with Pleasant Password Server for credential management
- Support certificate management with password protection

## Platform-Specific Notes

### Windows
- Base directory: `C:\gkretail`
- Firebird: `C:\Program Files\Firebird\Firebird_3_0`
- Jaybird: `C:\gkretail\Jaybird`
- Script extension: `.ps1`

### Linux
- Base directory: `/usr/local/gkretail`
- Firebird: `/opt/firebird`
- Jaybird: `/usr/local/gkretail/Jaybird`
- Script extension: `.sh`
- Requires special mousewheel handling (Button-4/Button-5 events)

## Recent Features & Architectural Changes

### Major Code Refactoring (November 2025)
The codebase underwent a comprehensive refactoring that significantly improved maintainability while preserving all functionality:

**Key Achievements:**
- **Massive Code Reduction**: `generator.py` reduced from **3,592 lines to 899 lines** (75.0% reduction)
- **100% Test Coverage Maintained**: All **143 tests passing** throughout refactoring
- **Zero Regressions**: Generated output remains functionally identical to original
- **Clean Repository**: All backup files and old versions archived in `archive/` directory

**New Modular Structure:**
- Created dedicated `generators/` subdirectory with specialized modules
- Extracted GKInstall script generation (771 lines) to `gk_install_generator.py`
- Extracted helper file operations to `helper_file_generator.py`
- Extracted launcher template generation to `launcher_generator.py`
- Extracted onboarding script generation to `onboarding_generator.py`
- Extracted offline package helpers to `offline_package_helpers.py`
- Added `version.py` utilities module

**Refactoring Principles Applied:**
- **Extract Method Pattern**: Large methods (40-800+ lines) extracted to dedicated functions
- **Module Organization**: Related functions grouped into dedicated modules
- **Delegation Pattern**: Original `generator.py` delegates to specialized modules
- **Test-Driven Refactoring**: All tests maintained and passing throughout
- **Incremental Approach**: Refactoring done in small, verifiable steps

**Regression Fixes (Post-Refactoring):**
All regressions identified and fixed with comprehensive testing:
- ✅ Function Pack API testing fully restored (all 5 components, FP/FPD scope)
- ✅ Config-Service API testing fully restored (all 5 components, version lists)
- ✅ Token generation logging enhanced with detailed [TOKEN GEN] output
- ✅ Offline package creator function signatures corrected
- ✅ Download paths fixed to use configured output directory (not project root)
- ✅ DSG API Browser context menu downloads now use output directory

### Multi-Environment Support (feature/multi-environment branch)
- Per-environment configurations with separate credentials
- Environment detection via 3-group hostname patterns
- OAuth2 token caching per environment

### CLI Parameter Overrides
Generated scripts support CLI parameters with highest priority:
- `--storeId` / `--workstationId` (Windows PowerShell)
- `--storeId` / `--workstationId` (Linux Bash, case-insensitive handling)

### Enhanced Detection Priority
Five-tier detection system ensures automation compatibility while supporting manual installation.

### Password Encoding Fixes
Consistent base64 encoding between password generation and environment manager for AUTH token generation.

## Working with This Codebase

### Working with the Modular Structure (Post-Refactoring)

The November 2025 refactoring introduced a modular architecture. When making changes:

**Generator Module (`generator.py`):**
- Main orchestrator - delegates to specialized modules
- Coordinates overall build process
- Manages DSG API browser and download workers
- **When to modify**: Adding new component types, changing build orchestration

**Generator Modules (`generators/`):**
- **`gk_install_generator.py`**: Modify for GKInstall script changes (template variable replacement, detection logic)
- **`helper_file_generator.py`**: Modify for helper file structure changes
- **`launcher_generator.py`**: Modify for launcher template changes
- **`onboarding_generator.py`**: Modify for onboarding script changes
- **`offline_package_helpers.py`**: Modify for download/packaging logic
- **`template_processor.py`**: Modify for template processing and regex replacement

**Important**: All generator modules support dual import (both package and direct execution) via wrapper functions in `generator.py`.

### Adding a New Component
1. Update `helper_structure` in `generator.py`
2. Create launcher template in `helper/launchers/`
3. Create onboarding config in `helper/onboarding/`
4. Add to UI in `main.py`
5. Add version property mapping in `default_versions.json`
6. Update `gk_install_generator.py` if component needs special handling
7. Update `offline_package_helpers.py` if component supports offline packages

### Modifying Generated Scripts
1. Edit template files in `gk_install_builder/templates/`
2. Ensure all `@VARIABLE@` placeholders are defined in generator substitution (see `gk_install_generator.py`)
3. Test both Windows and Linux templates
4. Update main scripts, onboarding, and initialization scripts if needed
5. **Important**: Changes to detection logic go in `gk_install_generator.py`, not templates

### Adjusting Configuration Defaults
1. Modify `_get_default_config()` in `config.py`
2. Consider platform-specific defaults
3. Update UI default values in `main.py` if needed
4. Test with fresh configuration (delete `gk_install_config.json`)

### Running Tests After Changes
```bash
# Run all tests (should always pass - 143/143)
pytest tests/ -v

# Run specific test suites
pytest tests/unit/test_generator_core.py -v
pytest tests/unit/test_generator_integration.py -v
pytest tests/unit/test_api_integration.py -v
```

## Important Notes

- **All 143 tests must pass** - The codebase maintains 100% test coverage post-refactoring
- Templates are platform-specific; always update both `.ps1` (Windows) and `.sh` (Linux) versions
- Generated scripts embed credentials—consider security implications
- WebDAV operations bypass SSL verification (intended for internal retail networks)
- Config auto-save uses 1-second debounce; changes are not saved immediately
- The `feature/multi-environment` branch contains multi-tenancy features not yet merged to main
- **Archive directory** (`archive/`) contains old code versions and refactoring documentation for historical reference

## Archive Directory Structure

The `archive/` directory preserves the refactoring history:

```
archive/
├── backups/               # Backup files created during development
├── old_versions/          # Previous versions of main.py from refactoring phases
├── pre-refactoring/       # Complete pre-refactoring codebase snapshot
├── refactoring_docs/      # Refactoring documentation and session summaries
└── temp/                  # Temporary files from development
```

These files are kept for historical reference and comparison but are not part of the active codebase. See `archive/README.md` for details.
