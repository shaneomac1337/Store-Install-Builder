# Store Install Builder - Complete Codebase Analysis Plan

## Project Overview
The Store Install Builder is a comprehensive Python GUI application designed to create installation packages for retail store environments. It supports multiple GK Software components (POS, WDM, Flow Service, LPA Service, StoreHub Service) across Windows and Linux platforms.

## Architecture Analysis

### Core Components

#### 1. Main Application (`gk_install_builder/main.py`)
- **Purpose**: Primary GUI application entry point
- **Framework**: CustomTkinter for modern UI components
- **Key Features**:
  - Scrollable configuration interface
  - Auto-save functionality with visual feedback
  - WebDAV browser integration
  - KeePass password management integration
  - Detection settings management
  - Launcher settings editor
  - Offline package creator
  - Platform-specific configuration handling
  - Certificate generation capabilities
  - Comprehensive tooltip system

#### 2. Configuration Management (`gk_install_builder/config.py`)
- **Purpose**: Centralized configuration handling with auto-save
- **Key Features**:
  - JSON-based configuration persistence (`gk_install_config.json`)
  - Widget registration system for automatic updates
  - Debounced save operations (1-second delay)
  - Thread-safe save operations with status indicators
  - Visual save status indicators ("Saving...", "Saved", error messages)
  - Default configuration generation with platform-specific defaults
  - Entry widget lifecycle management with safe cleanup
  - Fixed value support for read-only entries

#### 3. Project Generation (`gk_install_builder/generator.py`) - 3,711 lines
- **Purpose**: Core project generation and WebDAV operations
- **Key Features**:
  - **WebDAV Integration**: File browsing and downloading from remote servers
  - **Template Processing**: Dynamic script generation from templates
  - **Cross-Platform Support**: Windows (PowerShell) and Linux (Bash) scripts
  - **Component-Specific Versions**: Individual version management per component
  - **Detection Integration**: Hostname and file-based detection systems
  - **Offline Package Creation**: Download and organize installation files
  - **Progress Tracking**: Multi-threaded downloads with real-time progress
  - **File Selection Dialogs**: User-friendly component selection
  - **Launcher Template Generation**: Customizable launcher configurations
  - **Store Initialization**: Dynamic store setup scripts
  - **IP-based Store Detection**: Runtime store mapping from DSG server
  - **WDM Hardcoding**: Automatic WorkstationID=200 for WDM components

#### 4. Detection Management (`gk_install_builder/detection.py`)
- **Purpose**: Store and workstation ID automatic detection
- **Key Features**:
  - **Hostname Detection**: Regex-based hostname parsing with platform-specific patterns
  - **File Detection**: Station file parsing for IDs with configurable paths
  - **Base Directory Support**: Centralized station file management
  - **Custom File Paths**: Component-specific detection files
  - **Regex Testing**: Built-in validation and testing capabilities
  - **Code Generation**: Dynamic script code generation for both platforms

#### 5. Pleasant Password Integration (`gk_install_builder/pleasant_password_client.py`)
- **Purpose**: KeePass/Pleasant Password Server integration
- **Key Features**:
  - OAuth2 authentication with bearer token support
  - RESTful API client for password management
  - Folder and entry management
  - Password retrieval with encryption
  - Two-factor authentication support

### Template System

#### Script Templates (`gk_install_builder/templates/`)
- **GKInstall Scripts**: Main installation scripts (PowerShell/Bash)
- **Onboarding Scripts**: Component onboarding automation
- **Store Initialization**: Store setup and configuration with dynamic system types

#### Helper Structure (`helper/`)
- **Launchers**: Component-specific launcher configurations
- **Onboarding**: JSON configuration files for component onboarding
- **Tokens**: Authentication and password files (Base64 encoded)
- **Init**: Store initialization configurations
- **Structure**: Store and station structure definitions
- **StoreHub**: Update configuration for StoreHub service

## Data Flow Architecture

### 1. Configuration Flow
```
User Input → Widget Registration → Auto-Save (Debounced) → JSON Persistence
     ↓
Configuration Loading → Widget Population → Real-time Updates → Status Display
```

### 2. Project Generation Flow
```
Configuration → Template Selection → Variable Replacement → Script Generation
     ↓
Helper Files → Component Settings → Output Directory Structure → Store Initialization
```

### 3. Detection Flow
```
Hostname Detection → Regex Matching → Store/Workstation ID Extraction
     ↓
File Detection → Station File Parsing → ID Validation → Manual Input Fallback
     ↓
IP-based Detection → DSG Server Mapping → Runtime Store Resolution
```

### 4. WebDAV Integration Flow
```
Connection → Authentication → Directory Browsing → File Selection → Download Management
     ↓
Progress Tracking → Multi-threading → Error Handling → Completion Notification
```

## Key Technical Features

### 1. Cross-Platform Support
- **Windows**: PowerShell scripts, Windows-specific paths and configurations
- **Linux**: Bash scripts, Unix-style paths and permissions (chmod 755)
- **Platform Detection**: Automatic platform-specific defaults

### 2. Component Management
- **POS (Point of Sale)**: Retail transaction processing
- **WDM** (Wall Device Manager): Data synchronization with hardcoded WorkstationID=200
- **Flow Service**: Business process automation
- **LPA Service**: Local Processing Agent
- **StoreHub Service**: Central store management with Firebird database integration

### 3. Version Management
- **Global Versioning**: Single version for all components
- **Component-Specific Versioning**: Individual version override capability
- **Dynamic Version Resolution**: Fallback logic for missing versions
- **Template Variable Replacement**: @VERSION@ placeholders in templates

### 4. Security Features
- **SSL Certificate Management**: P12 certificate handling and copying
- **Password Encryption**: Base64 encoding for sensitive data
- **Pleasant Password Integration**: Secure credential management
- **WebDAV Authentication**: Secure remote file access with SSL verification disabled

### 5. Detection Systems
- **Hostname Detection**: Configurable regex patterns for store/workstation extraction
- **File Detection**: Station file parsing with configurable paths and filenames
- **IP-based Detection**: Runtime store mapping from DSG server
- **Manual Fallback**: User input when automatic detection fails
- **Validation**: Input validation and format checking

### 6. Offline Package Creation
- **Component Downloads**: Automated file retrieval from WebDAV with version-specific paths
- **Dependency Management**: Java, Tomcat, and Jaybird driver downloads
- **Progress Tracking**: Real-time download progress with cancellation support
- **File Organization**: Structured output directory creation
- **Platform-specific Selection**: Automatic filtering based on target platform

## Configuration Schema

### Main Configuration
```json
{
  "project_name": "string",
  "base_url": "string",
  "version": "string",
  "platform": "Windows|Linux",
  "use_hostname_detection": "boolean",
  "use_version_override": "boolean",
  "component_versions": {
    "pos_version": "string",
    "wdm_version": "string",
    "flow_service_version": "string",
    "lpa_service_version": "string",
    "storehub_service_version": "string"
  },
  "system_types": {
    "pos_system_type": "string",
    "wdm_system_type": "string",
    "flow_service_system_type": "string",
    "lpa_service_system_type": "string",
    "storehub_service_system_type": "string"
  },
  "detection_config": {
    "file_detection_enabled": "boolean",
    "use_base_directory": "boolean",
    "base_directory": "string",
    "custom_filenames": "object",
    "detection_files": "object",
    "hostname_detection": {
      "windows_regex": "string",
      "linux_regex": "string",
      "test_hostname": "string"
    }
  },
  "launcher_settings": {
    "pos_launcher_settings": "object",
    "wdm_launcher_settings": "object",
    "flow_service_launcher_settings": "object",
    "lpa_service_launcher_settings": "object",
    "storehub_service_launcher_settings": "object"
  },
  "platform_dependencies": {
    "JAVA": "boolean",
    "TOMCAT": "boolean",
    "JAYBIRD": "boolean"
  },
  "security": {
    "ssl_password": "string",
    "certificate_path": "string",
    "webdav_username": "string",
    "webdav_password": "string",
    "launchpad_oauth2": "string",
    "eh_launchpad_username": "string",
    "eh_launchpad_password": "string"
  }
}
```

## Dependencies

### Core Dependencies
- **customtkinter**: Modern GUI framework
- **requests**: HTTP client for WebDAV and API calls
- **webdavclient3**: WebDAV protocol implementation
- **urllib3**: HTTP library with SSL support
- **pillow**: Image processing for GUI

### Development Dependencies
- **setuptools**: Package building
- **wheel**: Package distribution
- **pyinstaller**: Executable creation

## Build and Distribution

### Executable Creation
- **PyInstaller**: Creates standalone executables (`StoreInstallBuilder.spec`)
- **Cross-Platform**: Separate builds for Windows and Linux
- **Asset Bundling**: Templates and helper files included

### Project Structure
```
Store-Install-Builder/
├── gk_install_builder/
│   ├── main.py              # Main application
│   ├── config.py            # Configuration management
│   ├── generator.py         # Project generation (3,711 lines)
│   ├── detection.py         # Detection management
│   ├── pleasant_password_client.py  # KeePass integration
│   ├── assets/              # Application assets
│   └── templates/           # Script templates
├── helper/                  # Helper files and configurations
├── requirements.txt         # Python dependencies
├── StoreInstallBuilder.spec # PyInstaller specification
└── test.cases             # Test cases
```

## Usage Workflows

### 1. Basic Project Generation
1. Configure project settings (name, URL, version)
2. Select platform (Windows/Linux)
3. Configure component system types
4. Set up detection preferences (hostname/file/IP-based)
5. Generate project with scripts and helper files

### 2. Offline Package Creation
1. Configure WebDAV connection
2. Select components to download
3. Choose platform dependencies (Java, Tomcat, Jaybird)
4. Monitor download progress with real-time updates
5. Organize downloaded files for offline installation

### 3. Detection Configuration
1. Enable/disable hostname detection
2. Configure regex patterns for hostname parsing
3. Set up file detection paths and filenames
4. Test detection patterns with sample hostnames
5. Configure IP-based detection fallback

### 4. Store Initialization
1. Configure store-specific settings
2. Set up StoreHub database parameters
3. Configure component-specific ports and settings
4. Generate store initialization scripts
5. Deploy with proper system types
## Recent Enhancements

### 1. IP-based Store Detection
- **Store IP Mapping File**: Downloads `store_ip_mapping.properties` from DSG server at runtime
- **Mapping URL**: `https://{base_url}/dsg/content/cep/SoftwarePackage/store_ip_mapping.properties`
- **File Format**: `{StoreID}:{IPAddress}` (e.g., `1674:192.168.1.100`)
- **Download Methods**:
  - Primary: `curl.exe` with fallback to PowerShell WebClient
  - Bash: `curl` with fallback to `wget`
- **IP Detection**: Automatically detects current machine IP and matches against mapping
- **Automatic store ID resolution**: Maps IP address to store number
- **Fallback**: Manual input when mapping fails or file unavailable

#### Key Implementation Files
- **PowerShell Template**: [`gk_install_builder/templates/GKInstall.ps1.template`](gk_install_builder/templates/GKInstall.ps1.template:948) (lines 948-1078)
- **Bash Template**: [`gk_install_builder/templates/GKInstall.sh.template`](gk_install_builder/templates/GKInstall.sh.template:738) (lines 738-841)
- **Generator Integration**: [`gk_install_builder/generator.py`](gk_install_builder/generator.py:190) (IP mapping comments and template processing)
- **Gitignore Reference**: [`.gitignore`](.gitignore:232) (line 232 - excludes local mapping files)

### 2. Store IP Mapping System Implementation

The application implements a sophisticated runtime store mapping system that automatically downloads and processes IP-to-store mappings:

#### File Download Process
- **PowerShell Implementation** (lines 948-1078 in `GKInstall.ps1.template`):
  - Primary method: `curl.exe` with comprehensive error handling
  - Fallback method: `WebClient.DownloadString()` with memory-first approach
  - File validation: Size and content verification before processing
  - Error cleanup: Automatic removal of failed/empty downloads

- **Bash Implementation** (lines 738-841 in `GKInstall.sh.template`):
  - Primary method: `curl` with silent mode and error detection
  - Fallback method: `wget` with quiet output
  - Download validation: File existence and size checks
  - Cleanup handling: Removal of partial or failed downloads

#### IP Detection and Matching
- **PowerShell IP Detection**:
  ```powershell
  Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.IPAddress -ne "127.0.0.1" -and
    ($_.PrefixOrigin -eq "Dhcp" -or $_.PrefixOrigin -eq "Manual")
  }
  ```
  - Fallback: WMI-based detection using `Win32_NetworkAdapterConfiguration`

- **Bash IP Detection**:
  ```bash
  hostname -I | awk '{print $1}'  # Primary method
  ip route get 8.8.8.8 | awk '{print $7}'  # Fallback method
  ```

#### Mapping File Processing
- **File Format**: Simple text format with colon-separated values (`StoreID:IP`)
- **Parsing Logic**: Line-by-line processing with regex matching
- **Store ID Extraction**: Automatic assignment when IP match found
- **Integration**: Seamless integration with existing detection flow

#### Error Handling and Fallbacks
- **Download Failures**: Graceful degradation to manual input
- **Network Issues**: Multiple download method attempts
- **File Corruption**: Content validation and cleanup
- **IP Detection Failures**: Multiple IP detection methods

### 3. WDM Component Hardcoding
- Automatic WorkstationID=200 assignment for WDM components
- Bypasses manual input for WDM installations
- Integrated into detection flow


### 3. Enhanced Template Processing
- Dynamic system type replacement in store initialization
- Improved variable substitution with @PLACEHOLDER@ format
- Platform-specific template selection

### 4. Improved Error Handling
- Comprehensive download error reporting
- User-friendly dialog boxes for file conflicts
- Graceful fallback mechanisms

## Future Enhancement Areas

### 1. User Interface
- Enhanced progress indicators with file-specific tracking
- Better error handling and user feedback
- Improved file selection interfaces with smart defaults
- Configuration validation and real-time feedback

### 2. Integration
- Additional password managers beyond Pleasant Password
- More WebDAV server types and authentication methods
- Cloud storage integration for offline packages
- API-based component management

### 3. Automation
- Batch processing capabilities for multiple stores
- Scheduled operations and automated deployments
- Configuration templates and presets
- Deployment automation with rollback capabilities

## Conclusion

The Store Install Builder is a sophisticated application that successfully abstracts the complexity of retail software deployment across multiple platforms and components. Its modular architecture, comprehensive configuration management, and robust detection systems make it a powerful tool for retail environment setup and maintenance.

The application demonstrates excellent software engineering practices including:
- Separation of concerns with clear module boundaries
- Configuration-driven behavior with extensive customization
- Cross-platform compatibility with platform-specific optimizations
- User-friendly interface design with modern GUI components
- Comprehensive error handling and graceful degradation
- Extensible architecture supporting future enhancements

This analysis provides a complete understanding of the application's capabilities, architecture, and potential for future development. The recent enhancements show active development and continuous improvement of the platform.