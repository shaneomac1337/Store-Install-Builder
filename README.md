# GK Install Builder

## Overview

GK Install Builder is a powerful GUI application designed to streamline the creation of installation packages for retail store environments. It automates the generation of platform-specific installation scripts, configuration files, and deployment packages for both Windows and Linux systems.

## Features

- **Cross-Platform Support**: Generate installation packages for both Windows and Linux environments
- **Customizable Templates**: Configure and customize installation templates for different components
- **Automatic Detection**: Intelligent detection of store and workstation IDs through hostname patterns or station files
- **WebDAV Integration**: Browse and interact with WebDAV repositories for file management
- **Password Management**: Integration with Pleasant Password Server for secure credential management
- **User-Friendly Interface**: Modern GUI built with CustomTkinter for an enhanced user experience

## Components

The application supports configuration and deployment of various retail components:
- Point of Sale (POS)
- Wall Device Manager (WDM)
- Flow Service
- LPA Service
- StoreHub Service

## Generated Scripts and Files

Based on the selected configuration, GK Install Builder generates the following platform-specific scripts and files:

### Installation Scripts

- **GKInstall Scripts**:
  - `GKInstall.ps1` (Windows PowerShell)
  - `GKInstall.sh` (Linux Bash)
  - Handles detection of store and workstation information
  - Configures environment variables and system settings
  - Manages component installation and configuration

### Onboarding Scripts

- **Onboarding Scripts**:
  - `onboarding.ps1` (Windows PowerShell)
  - `onboarding.sh` (Linux Bash)
  - Configures initial system setup
  - Sets up network and environment configuration

### Store Initialization Scripts

- **Store Initialization Scripts**:
  - `store-initialization.ps1` (Windows PowerShell)
  - `store-initialization.sh` (Linux Bash)
  - Handles store-specific configuration and setup

### Component Launchers

- **Launcher Templates**:
  - `launcher.pos.template` - Point of Sale launcher
  - `launcher.wdm.template` - Warehouse & Distribution Management launcher
  - `launcher.flow-service.template` - Flow Service launcher
  - `launcher.lpa-service.template` - LPA Service launcher
  - `launcher.storehub-service.template` - StoreHub Service launcher

### Configuration Files

- **JSON Configuration Files**:
  - Component-specific configuration
  - Environment settings
  - Connection parameters

## Technical Architecture

The application follows a modular architecture with these key components:

- **Main Application (GKInstallBuilder)**: The core GUI and application controller
- **Project Generator**: Handles the generation of installation scripts and configuration files
- **Config Manager**: Manages application configuration and persistence
- **Detection Manager**: Handles automatic detection of store and workstation information
- **WebDAV Browser**: Provides WebDAV connectivity for remote file operations
- **Pleasant Password Client**: Interfaces with the Pleasant Password Server API

## Technologies Used

- **Python**: Core programming language
- **CustomTkinter**: Enhanced Tkinter library for modern UI components
- **WebDAV Client**: For remote file system operations
- **Requests**: For HTTP communication with APIs

## Installation

### Prerequisites

- Python 3.7 or higher
- Required Python packages (see requirements.txt)

### Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python -m gk_install_builder.main
   ```

### Building Standalone Executable

To create a standalone executable:

```
pyinstaller GKInstallBuilder.spec
```

## Usage

1. **Configuration**: Set up your environment configuration including URLs, paths, and credentials
2. **Component Selection**: Select which components to include in your installation package
3. **Template Customization**: Customize installation templates as needed
4. **Generation**: Generate the installation package with all required files
5. **Deployment**: Deploy the generated package to target systems

## File Structure

- **gk_install_builder/**: Main application package
  - **assets/**: Images and other static resources
  - **templates/**: Installation script templates
  - **main.py**: Application entry point
  - **generator.py**: Installation package generator
  - **config.py**: Configuration management
  - **detection.py**: Store/workstation detection logic
  - **pleasant_password_client.py**: Password management client

## Configuration

The application stores its configuration in `gk_install_config.json`. This includes:

- Environment settings
- Base URLs and paths
- Component-specific configurations
- Detection settings
- Template customizations

## Advanced Features

### Custom Hostname Detection

The application supports custom regex patterns for hostname detection, allowing for flexible adaptation to different naming conventions in various environments.

### File-Based Detection

When hostname detection is not available, the application can use file-based detection to identify store and workstation information.

### WebDAV Integration

The WebDAV browser allows for easy navigation and selection of remote files and directories, simplifying the process of locating and using remote resources.

### Password Management

Integration with Pleasant Password Server provides secure access to credentials needed for various components and services.
