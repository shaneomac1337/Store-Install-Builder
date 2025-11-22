# GK Install Builder

## Overview

GK Install Builder is a powerful Python GUI application designed to streamline the creation of installation packages for retail store environments. It automates the generation of platform-specific installation scripts, configuration files, and deployment packages for both Windows and Linux systems.

The application supports **multi-environment deployments**, **automated CLI-based installations**, and **intelligent detection** of store and workstation identifiers, making it ideal for large-scale retail installations.

## Key Features

- **Cross-Platform Support**: Generate installation packages for both Windows (PowerShell) and Linux (Bash) environments
- **CLI Parameter Overrides**: Support for automated deployments with `--storeId` and `--workstationId` command-line parameters
- **Multi-Environment Support**: Manage multiple environments (DEV, QA, PROD) with per-environment credentials and configurations
- **Five-Tier Detection System**: Intelligent detection of store and workstation IDs with configurable priority:
  1. CLI parameters (highest priority)
  2. Update mode (preserve existing configuration)
  3. Hostname pattern detection
  4. File-based detection (.station files)
  5. Manual user input
- **REST API Integration**: Browse and interact with Digital Content Service REST API for file management
- **OAuth2 Integration**: Automatic token generation and caching for API authentication
- **Password Management**: Integration with Pleasant Password Server (KeePass) for secure credential management
- **Version Management**: Automatic version retrieval from Employee Hub Service API and Config-Service API with fallback defaults
- **Offline Package Generation**: Create self-contained installation packages for environments without internet access
- **Certificate Management**: Import or generate SSL certificates (.p12) with password protection
- **User-Friendly Interface**: Modern GUI built with CustomTkinter featuring a wizard-style interface for first-time users
- **Auto-Save Configuration**: Intelligent auto-save with 1-second debounce to prevent data loss

## Supported Components

The application supports configuration and deployment of various retail components:
- **POS** (Point of Sale)
- **WDM** (Wall Device Manager)
- **Flow Service**
- **LPA Service**
- **StoreHub Service**
- **DriveService** (special handling)

## Generated Scripts and Files

Based on the selected configuration, GK Install Builder generates the following platform-specific scripts and files:

### Installation Scripts

- **GKInstall Scripts**:
  - `GKInstall.ps1` (Windows PowerShell)
  - `GKInstall.sh` (Linux Bash)
  - Handles five-tier detection of store and workstation information
  - Configures environment variables and system settings
  - Manages component installation and configuration
  - Supports CLI parameter overrides for automation

### Onboarding Scripts

- **Onboarding Scripts**:
  - `onboarding.ps1` (Windows PowerShell)
  - `onboarding.sh` (Linux Bash)
  - Configures initial system setup
  - Sets up network and environment configuration
  - Generates OAuth2 tokens for API authentication

### Store Initialization Scripts

- **Store Initialization Scripts**:
  - `store-initialization.ps1` (Windows PowerShell)
  - `store-initialization.sh` (Linux Bash)
  - Handles store-specific configuration and setup

### Component Launchers

- **Launcher Templates**:
  - `launcher.pos.template` - Point of Sale launcher
  - `launcher.wdm.template` - Wall Device Manager launcher
  - `launcher.flow-service.template` - Flow Service launcher
  - `launcher.lpa-service.template` - LPA Service launcher
  - `launcher.storehub-service.template` - StoreHub Service launcher

### Configuration Files

Located in the `helper/` directory of generated packages:

- **Onboarding Configs** (`helper/onboarding/`):
  - Component-specific JSON configurations for each service

- **Authentication Tokens** (`helper/tokens/`):
  - `access_token.txt` - OAuth2 access token
  - `basic_auth_password.txt` - Basic authentication password
  - `form_password.txt` - Form-based authentication password

- **Initialization Configs** (`helper/init/`):
  - `get_store.json` - Store initialization configuration

- **StoreHub Configs** (`helper/storehub/`):
  - `update_config.json` - StoreHub update configuration

- **Directory Structure** (`helper/structure/`):
  - `create_structure.json` - Directory structure definition

## Technical Architecture

The application follows a modular architecture with these key components:

### Core Components

- **Main Application** (`gk_install_builder/main.py` - ~1,392 lines): The core GUI and application controller
  - CustomTkinter-based interface with wizard mode for first-time users
  - Multi-section configuration form with auto-save
  - Integration manager for all feature modules

- **Project Generator** (`gk_install_builder/generator.py` - 899 lines, refactored): Main orchestrator for installation package generation
  - Coordinates all generation modules and manages the overall build process
  - Creates complete directory structure with helper files
  - Delegates to specialized generator modules for specific tasks
  - Supports both Windows (.ps1) and Linux (.sh) scripts

- **Generator Modules** (`gk_install_builder/generators/`): Specialized script generation modules
  - **gk_install_generator.py** (771 lines): GKInstall script generation with template variable replacement, hostname/file detection code injection, and platform-specific regex handling
  - **helper_file_generator.py**: Helper file operations, store initialization scripts, component files, JSON configs, and multi-environment support
  - **launcher_generator.py**: Component launcher template generation with per-component settings
  - **onboarding_generator.py**: Onboarding script generation for both platforms
  - **template_processor.py**: Hostname regex replacement and template token processing
  - **offline_package_helpers.py**: File download threading, progress tracking, and package handling

- **Config Manager** (`gk_install_builder/config.py`): Manages application configuration and persistence
  - JSON-based configuration storage (`gk_install_config.json`)
  - Auto-save with 1-second debounce to reduce file I/O
  - Entry widget registration for automatic two-way data binding
  - Platform-specific defaults (Windows: `C:\gkretail`, Linux: `/usr/local/gkretail`)

- **Detection Manager** (`gk_install_builder/detection.py`): Handles automatic detection of store and workstation information
  - Five-tier priority detection system
  - Hostname-based detection with customizable regex patterns (2-group and 3-group patterns)
  - File-based detection using .station files
  - Platform-specific regex patterns for Windows and Linux

- **Environment Manager** (`gk_install_builder/environment_manager.py` - 492 lines): Multi-environment and multi-tenancy support
  - Per-environment configurations with separate credentials
  - Environment aliasing and cloning
  - OAuth2 token caching per environment
  - Automatic environment detection via hostname patterns

- **Generator Configuration** (`gk_install_builder/gen_config/generator_config.py` - 156 lines): Generator configuration management
  - Centralized configuration for generation processes
  - Configuration validation and defaults

- **Pleasant Password Client** (`gk_install_builder/pleasant_password_client.py`): Interfaces with the Pleasant Password Server API
  - OAuth2 authentication
  - Folder and credential browsing
  - Password retrieval for automated configuration
  - Session-level credential caching

### Feature Modules

Located in `gk_install_builder/features/`:

- **auto_fill.py**: Auto-populate fields from base URL
  - Extracts project code from URL
  - Detects system types (product vs customer URLs)
  - Sets platform-specific defaults

- **certificate_manager.py**: SSL certificate management
  - Import existing .p12 certificates
  - Generate new certificates
  - Password protection

- **platform_handler.py**: Windows/Linux platform switching
  - Platform-specific default paths
  - Script extension handling

- **version_manager.py**: Component version management
  - Employee Hub Service API integration
  - Config-Service API integration
  - Fallback to default versions

### Integration Modules

Located in `gk_install_builder/integrations/`:

- **api_client.py**: API integration and testing
  - OAuth2 token generation
  - Employee Hub Service API client
  - Config-Service API client
  - Token validation and testing

- **keepass_handler.py**: Pleasant Password Server integration
  - OAuth2 authentication flow
  - Credential browsing and retrieval

### Dialog Modules

Located in `gk_install_builder/dialogs/`:

- **detection_settings.py**: Store/Workstation detection configuration dialog
- **launcher_settings.py**: Component launcher editor dialog
- **offline_package.py**: Offline package creator dialog
- **download_dialogs.py** (248 lines): Download progress dialogs
- **about.py**: About dialog

### Utility Modules

Located in `gk_install_builder/utils/`:

- **helpers.py**: JSON processing utilities
- **tooltips.py**: UI tooltip helpers
- **ui_colors.py**: Consistent color scheme
- **version.py**: Version management utilities
- **environment_setup.py** (42 lines): Environment setup utilities
- **file_operations.py** (128 lines): File operation utilities

## Technologies Used

- **Python 3.7+** (tested with Python 3.13.5)
- **CustomTkinter**: Enhanced Tkinter library for modern UI components
- **Requests**: HTTP communication with APIs
- **urllib3**: Advanced HTTP library features
- **Pillow**: Image handling for GUI
- **PyInstaller**: Standalone executable creation
- **setuptools/wheel**: Package management
- **pytest**: Test framework (development)

## Installation

### Prerequisites

- Python 3.7 or higher (tested with Python 3.13.5)
- Required Python packages (see requirements.txt)

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python -m gk_install_builder.main
   ```

### Development Setup

For development with testing capabilities:

```bash
# Install production dependencies
pip install -r requirements.txt

# Install test dependencies
pip install -r requirements-test.txt

# Run tests
pytest tests/

# Run with coverage
pytest --cov=gk_install_builder tests/
```

### Building Standalone Executable

To create a standalone executable:

```bash
pyinstaller StoreInstallBuilder.spec
```

Output location: `dist/GK Install Builder/GK Install Builder.exe`

## Usage

1. **Configuration**: Set up your environment configuration including URLs, paths, and credentials
2. **Component Selection**: Select which components to include in your installation package
3. **Detection Configuration**: Configure hostname patterns or file-based detection for automated identification
4. **Multi-Environment Setup** (optional): Configure multiple environments with separate credentials
5. **Template Customization**: Customize installation templates as needed
6. **Generation**: Generate the installation package with all required files
7. **Deployment**: Deploy the generated package to target systems

### CLI-Based Automated Installation

Generated scripts support CLI parameters for automated deployments:

**Windows:**
```powershell
.\GKInstall.ps1 -storeId "12345" -workstationId "001"
```

**Linux:**
```bash
./GKInstall.sh --storeId "12345" --workstationId "001"
```

These parameters have the highest priority in the detection system, enabling fully automated installations.

## File Structure

```
Store-Install-Builder/
├── gk_install_builder/              # Main application package
│   ├── assets/                      # Images and static resources
│   ├── core/                        # Core business logic
│   ├── dialogs/                     # Dialog windows (modals)
│   │   ├── about.py
│   │   ├── detection_settings.py
│   │   ├── launcher_settings.py
│   │   ├── offline_package.py
│   │   └── download_dialogs.py      # Download progress dialogs (248 lines)
│   ├── features/                    # Feature modules
│   │   ├── auto_fill.py
│   │   ├── certificate_manager.py
│   │   ├── platform_handler.py
│   │   └── version_manager.py
│   ├── generators/                  # Script generation modules (NEW)
│   │   ├── __init__.py
│   │   ├── gk_install_generator.py      # GKInstall script generation (771 lines)
│   │   ├── helper_file_generator.py     # Helper files and configs
│   │   ├── launcher_generator.py        # Component launcher templates
│   │   ├── onboarding_generator.py      # Onboarding scripts
│   │   ├── template_processor.py        # Template processing utilities
│   │   └── offline_package_helpers.py   # Offline package creation
│   ├── integrations/                # External service integrations
│   │   ├── api_client.py
│   │   └── keepass_handler.py
│   ├── models/                      # Data models
│   ├── templates/                   # Installation script templates
│   │   ├── GKInstall.ps1.template
│   │   ├── GKInstall.sh.template
│   │   ├── onboarding.ps1.template
│   │   ├── onboarding.sh.template
│   │   ├── store-initialization.ps1.template
│   │   └── store-initialization.sh.template
│   ├── ui/                          # UI utilities
│   │   └── helpers.py
│   ├── utils/                       # General utilities (EXPANDED)
│   │   ├── helpers.py               # JSON processing utilities
│   │   ├── tooltips.py
│   │   ├── ui_colors.py
│   │   ├── version.py               # Version management utilities (NEW)
│   │   ├── environment_setup.py     # Environment setup utilities (42 lines)
│   │   └── file_operations.py       # File operation utilities (128 lines)
│   ├── config.py                    # Configuration management
│   ├── detection.py                 # Store/workstation detection logic
│   ├── environment_manager.py       # Multi-environment support
│   ├── gen_config/                  # Generator configuration module
│   │   └── generator_config.py      # Generator config management (156 lines)
│   ├── generator.py                 # Installation package generator (899 lines, refactored)
│   ├── keepass_dialog.py            # KeePass dialog UI
│   ├── main.py                      # Application entry point
│   ├── pleasant_password_client.py  # Password management client
│   └── default_versions.json        # Fallback component versions
├── archive/                         # Archived refactoring files (NEW)
│   ├── backups/                     # Code backups
│   ├── old_versions/                # Previous file versions
│   ├── pre-refactoring/             # Complete pre-refactoring codebase snapshot
│   ├── refactoring_docs/            # Refactoring documentation
│   └── temp/                        # Temporary development files
├── helper/                          # Helper files (copied to output)
│   ├── launchers/                   # Component launcher templates
│   ├── onboarding/                  # Component onboarding configs
│   ├── tokens/                      # Authentication token files
│   ├── init/                        # Initialization configs
│   ├── storehub/                    # StoreHub-specific configs
│   └── structure/                   # Directory structure configs
├── tests/                           # Test suite
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   ├── e2e/                         # End-to-end tests
│   └── conftest.py                  # pytest configuration
├── docs/                            # Documentation
│   ├── cli-parameters-feature.md
│   └── detection-analysis.md
├── CLAUDE.md                        # AI assistant guidance
├── README.md                        # This file
├── requirements.txt                 # Production dependencies
├── requirements-test.txt            # Test dependencies
├── StoreInstallBuilder.spec         # PyInstaller build specification
├── CHANGELOG.html                   # Feature changelog
└── gk_install_config.json           # Application configuration
```

## Configuration

The application stores its configuration in two main files:

### Main Configuration (`gk_install_config.json`)

Includes:
- Project metadata (name, base URL, version)
- Platform selection (Windows/Linux)
- Component-specific versions and settings
- Detection configuration (hostname patterns, file paths)
- Security credentials
- WebDAV/REST API credentials

**Auto-Save Behavior**: The configuration automatically saves changes after a 1-second debounce period. This prevents excessive file I/O while ensuring no data loss.

**Platform-Specific Defaults**:
- **Windows**: Base directory `C:\gkretail`, Firebird `C:\Program Files\Firebird\Firebird_3_0`
- **Linux**: Base directory `/usr/local/gkretail`, Firebird `/opt/firebird`

### Environment Configuration (`environments.json`)

Includes (when using multi-environment features):
- Per-environment credentials and base URLs
- Tenant IDs for each environment
- Environment-specific detection patterns
- OAuth2 token caching per environment

## Detection System

The application implements a sophisticated five-tier detection priority system in generated scripts:

### Priority 0: CLI Parameters (Highest Priority)
Generated scripts accept command-line parameters:
- Windows PowerShell: `-storeId` and `-workstationId`
- Linux Bash: `--storeId` and `--workstationId`

These parameters override all other detection methods, enabling fully automated deployments.

### Priority 1: Update Mode
When updating an existing installation, the script reads Store ID and Workstation ID from the existing `station.properties` file, preserving the current configuration.

### Priority 2: Hostname Detection
Uses customizable regex patterns to extract identifiers from the hostname:

**2-Group Pattern**: `STORE-WORKSTATION`
- Example: `POS-12345-001` → Store: 12345, Workstation: 001

**3-Group Pattern**: `ENVIRONMENT-STORE-WORKSTATION`
- Example: `DEV-12345-001` → Environment: DEV, Store: 12345, Workstation: 001

Patterns are platform-specific and can be customized in the Detection Settings dialog.

### Priority 3: File-Based Detection
Searches for `.station` files in configurable locations:
- Windows: `C:\gkretail\config\.station`
- Linux: `/usr/local/gkretail/config/.station`

File format:
```
STORE_ID=12345
WORKSTATION_ID=001
```

### Priority 4: Manual Input
If all automated detection methods fail, the script prompts the user to manually enter Store ID and Workstation ID.

## Advanced Features

### CLI Parameter Overrides

The CLI parameter feature enables fully automated deployments without user interaction:

**Use Cases**:
- Automated deployment scripts
- Configuration management systems
- Mass rollouts to multiple stores
- CI/CD pipeline integration

**Example Automated Deployment**:
```powershell
# Deploy to multiple workstations
$stores = @("12345", "12346", "12347")
foreach ($store in $stores) {
    .\GKInstall.ps1 -storeId $store -workstationId "001"
}
```

### Multi-Environment Support

The Environment Manager allows configuration of multiple retail environments:

**Features**:
- Separate credentials per environment
- Environment-specific base URLs and tenant IDs
- Environment aliasing for quick switching
- Environment cloning for similar configurations
- OAuth2 token caching per environment

**Use Cases**:
- Development, QA, and Production environments
- Multi-tenant retail deployments
- Regional deployments with different infrastructure

### Custom Hostname Detection

Configure custom regex patterns for hostname detection to match your organization's naming conventions:

**Configuration**:
1. Open Detection Settings dialog
2. Define regex patterns for your naming convention
3. Test patterns with example hostnames
4. Platform-specific patterns for Windows and Linux

**Example Patterns**:
- Windows: `^POS-(\d+)-(\d+)$`
- Linux: `^pos-(\d+)-(\d+)$`

### File-Based Detection

When hostname detection is not available or suitable, file-based detection provides an alternative:

**Setup**:
1. Create `.station` file in configured location
2. Define STORE_ID and WORKSTATION_ID
3. Scripts automatically detect and use these values

**Advantages**:
- Works in environments with generic hostnames
- Easily updated without hostname changes
- Portable across different systems

### Password Management

Integration with Pleasant Password Server provides secure credential management:

**Features**:
- OAuth2 authentication flow (`/OAuth2/Token` endpoint)
- Hierarchical folder browsing
- Credential retrieval by entry ID
- Session-level credential caching
- Environment auto-detection from base URL

**Usage**:
1. Click "Browse KeePass" button
2. Authenticate with Pleasant Password Server
3. Navigate folder hierarchy
4. Select credential entry
5. Password automatically populates in GUI

### Version Management

Automatic version retrieval with multiple sources:

**Version Source Priority**:
1. **User Override**: Manually specified versions in GUI
2. **Employee Hub Service API**: Dynamic version retrieval via `/employee-hub-service/services/rest/v1/properties`
3. **Config-Service API**: Alternative version retrieval method (newer)
4. **Default Versions**: Fallback from `default_versions.json`

**API Integration**:
- Requires OAuth2 bearer token
- Uses tenant-id header for multi-tenancy
- Scope-based queries (FP for modified, FPD for defaults)

### Offline Package Generation

Create self-contained installation packages for environments without internet access:

**Package Contents**:
- Installation scripts
- Component packages
- Certificates
- Configuration files
- All dependencies

**Use Cases**:
- Secure environments without internet
- Compliance requirements
- Disconnected stores or workstations

### REST API Integration

The application includes `DSGRestBrowser` for Digital Content Service integration:

**Features**:
- Automatic OAuth2 token refresh on 401 errors
- Retry logic with new tokens
- File and directory browsing
- Remote resource selection

**Connection**:
- Base URL pattern: `https://BASE_URL/dsg/rest/...`
- Authentication: Bearer token
- Automatic session management

## Security Considerations

### Embedded Credentials
Generated installation packages contain embedded credentials (tokens, passwords) for automated deployment. Consider:
- Secure distribution channels for packages
- File system permissions on generated packages
- Regular credential rotation
- Environment-specific credential management

### Password Encoding
- Passwords are base64-encoded in generated scripts
- OAuth2 tokens are cached securely per environment
- Debug logging masks sensitive information

### SSL Certificate Handling
- Certificates (.p12) are password-protected
- Certificate passwords are embedded in generated scripts
- REST API SSL verification disabled for internal networks

### Authentication Methods
- OAuth2 for Pleasant Password Server
- OAuth2 for Employee Hub Service API
- Basic authentication for REST API endpoints

## Testing

### Test Suite

The project includes a comprehensive pytest-based test suite:

```bash
# Run all tests
pytest tests/

# Run unit tests only
pytest tests/unit/

# Run with coverage report
pytest --cov=gk_install_builder tests/

# Run specific test file
pytest tests/unit/test_config_management.py
```

### Test Organization
```
tests/
├── unit/                          # Unit tests for individual classes
│   ├── test_api_integration.py
│   ├── test_auto_fill.py
│   ├── test_config_management.py
│   ├── test_detection.py
│   ├── test_platform_handling.py
│   └── test_version_management.py
├── integration/                   # Integration tests
└── e2e/                          # End-to-end tests
```

### Test Coverage Areas
- Configuration management and persistence
- Auto-fill logic and URL parsing
- Detection pattern matching
- Platform switching and defaults
- Version management and API integration
- Multi-environment configuration

## Development

### Architecture Patterns

**Threading for Blocking Operations**:
All long-running operations use threading to keep the GUI responsive:
```python
import threading
thread = threading.Thread(target=blocking_operation, daemon=True)
thread.start()
```

**Platform-Specific Handling**:
- Path separators (Windows `\` vs Unix `/`)
- Default installation paths
- Hostname detection regex patterns
- Mousewheel events (Button-4/5 for Linux, MouseWheel for Windows/macOS)

**Template-Based Generation**:
- Simple `@VARIABLE@` token replacement (no complex templating engine)
- Easy to debug and modify
- Platform-specific templates clearly separated

**Configuration Auto-Save**:
- 1-second debounce to batch saves
- Entry widget registration for two-way data binding
- Platform-specific defaults on first run

### Adding New Components

1. Update `helper_structure` in `generator.py`
2. Create launcher template in `helper/launchers/`
3. Create onboarding config in `helper/onboarding/`
4. Add to UI in `main.py`
5. Add version property mapping in `default_versions.json`
6. Update detection config in `detection.py` if needed

### Modifying Generated Scripts

1. Edit template files in `gk_install_builder/templates/`
2. Ensure all `@VARIABLE@` placeholders are defined in generator substitution
3. Test both Windows and Linux templates
4. Update main scripts, onboarding, and initialization scripts consistently

### Code Style

- Follow PEP 8 style guidelines
- Use classes for major components
- Prefer composition over inheritance
- Avoid global state; manage via class instances
- Use docstrings and inline comments
- Provide tooltips and clear error dialogs for user guidance

### Refactoring Principles Applied

The November 2025 refactoring followed these key principles:

**Extract Method Pattern**:
- Large methods (40-800+ lines) extracted to dedicated functions
- Each function has a single, clear responsibility
- Wrapper methods maintained in original files for backward compatibility

**Module Organization**:
- Related functions grouped into dedicated modules (generators/, utils/)
- Clear separation of concerns (generation vs. utilities vs. UI)
- Dual-import strategy supports both package and direct execution

**Delegation Pattern**:
- Original `generator.py` delegates to specialized generator modules
- Main coordinator remains thin and focused on orchestration
- Extracted functions handle specific implementation details

**Test-Driven Refactoring**:
- All 143 tests maintained and passing throughout refactoring
- Zero regressions in functionality
- Generated output verified to match original byte-for-byte (except intentional improvements)

**Incremental Approach**:
- Refactoring done in small, verifiable steps
- Each extraction tested independently
- Backup files created at each major milestone
- All history preserved in archive/ directory

## Recent Enhancements

### Major Code Refactoring (November 2025)

The codebase underwent a comprehensive refactoring to improve maintainability, modularity, and code organization:

#### Key Achievements

- **Massive Code Reduction**: `generator.py` reduced from **3,592 lines to 899 lines** (75.0% reduction)
- **100% Test Coverage Maintained**: All **143 tests passing** throughout refactoring
- **Zero Regressions**: Generated output remains functionally identical to original
- **Clean Repository**: All backup files and old versions archived in `archive/` directory

#### New Modular Structure

Created dedicated `generators/` subdirectory with specialized modules:

- **`gk_install_generator.py`** (771 lines)
  - Extracted GKInstall script generation logic
  - Handles Windows (PowerShell) and Linux (Bash) script generation
  - Template variable replacement and hostname/file detection code injection
  - Platform-specific regex pattern handling

- **`helper_file_generator.py`**
  - Helper file copying and generation
  - Store initialization script creation
  - Component files and JSON configuration management
  - Launcher template generation coordination
  - Multi-environment JSON generation

- **`launcher_generator.py`**
  - Component launcher template generation
  - Per-component settings application
  - Template variable replacement for launchers

- **`onboarding_generator.py`**
  - Onboarding script generation for both platforms
  - Environment configuration and setup

- **`template_processor.py`**
  - Hostname regex replacement for PowerShell and Bash
  - Template token processing utilities

- **`offline_package_helpers.py`**
  - File download threading and progress tracking
  - Platform dependency processing
  - Component package handling

#### Utility Modules

Created `utils/` subdirectory for shared functionality:

- **`version.py`**
  - Component version determination logic
  - System type to version mapping
  - Version override handling

- **`helpers.py`**
  - URL replacement in JSON files
  - Common utility functions

#### Benefits of Refactoring

✅ **Improved Maintainability**: Each module has a single, clear responsibility
✅ **Better Testability**: Smaller, focused functions easier to test
✅ **Enhanced Readability**: Reduced cognitive load with smaller files
✅ **Easier Debugging**: Clear separation of concerns simplifies troubleshooting
✅ **Future Development**: Modular structure makes adding features easier
✅ **Code Reusability**: Extracted functions can be reused across modules

#### Backward Compatibility

- ✅ All existing functionality preserved
- ✅ Generated scripts identical to original (except intentional improvements)
- ✅ Configuration format unchanged
- ✅ API interfaces maintained
- ✅ Dual-import strategy supports both package and direct execution

#### Archive Structure

Old code preserved in `archive/` directory:
- `archive/backups/` - Backup files from refactoring
- `archive/old_versions/` - Previous versions of main.py
- `archive/pre-refactoring/` - Complete pre-refactoring codebase snapshot
- `archive/refactoring_docs/` - Detailed refactoring documentation
- `archive/temp/` - Temporary development files

### CLI Parameter Overrides
Generated scripts now support `--storeId` and `--workstationId` CLI parameters with highest priority in the detection system, enabling fully automated deployments.

### Multi-Environment Manager
Environment Manager module provides multi-tenancy support with per-environment credentials, OAuth2 token caching, and environment-specific configurations.

### Enhanced Security
- Password encoding consistency fixes
- OAuth debug logging masks sensitive information
- Linux base64 password decoding improvements
- PowerShell case-insensitive variable handling

## Platform-Specific Notes

### Windows
- Default base directory: `C:\gkretail`
- Firebird path: `C:\Program Files\Firebird\Firebird_3_0`
- Jaybird path: `C:\gkretail\Jaybird`
- Uses PowerShell scripts (`.ps1`)
- CLI parameters use PowerShell syntax: `-storeId`, `-workstationId`

### Linux
- Default base directory: `/usr/local/gkretail`
- Firebird path: `/opt/firebird`
- Jaybird path: `/usr/local/gkretail/Jaybird`
- Uses Bash scripts (`.sh`)
- Requires special mousewheel handling (Button-4/Button-5 events)
- CLI parameters use Unix syntax: `--storeId`, `--workstationId`

## Documentation

For more detailed information:

- **CLAUDE.md**: Guidance for Claude Code AI assistant with architectural patterns and development workflows
- **docs/cli-parameters-feature.md**: Detailed CLI parameter documentation
- **docs/detection-analysis.md**: In-depth detection mechanism analysis
- **CHANGELOG.html**: Feature changelog and version history

## Support

For issues, feature requests, or contributions, please contact the development team or refer to the internal documentation portal.
