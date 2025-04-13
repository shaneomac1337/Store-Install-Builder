# GK Install Builder - Essential Guide

## Getting Started with GK Install Builder.exe

### STEP 1: Launch the Application
- [ ] Locate the downloaded **GK Install Builder.exe** file
- [ ] Double-click to start the application
- [ ] Wait for the main interface to load

> **NOTE:** The first time you run GK Install Builder, it uses a wizard mode that progressively reveals sections. Initially, you'll only see the basic Project Configuration section.

### STEP 2: Configure Project Settings
- [ ] Enter your project name (e.g., "Store123" or "Customer ABC")
- [ ] Enter your cloud4retail environment URL (e.g., "customer.cloud4retail.co")
- [ ] Enter the version number for this installation (e.g., "v1.0.0")
- [ ] Click the **Continue** button to proceed

### STEP 3: Select Platform
- [ ] Choose between **Windows** or **Linux** deployment
- Additional configuration sections will appear

### STEP 4: Configure Authentication
- [ ] Enter the password for Basic Auth authentication

### STEP 5: Certificate Configuration
- For existing certificate: Click **Browse** to locate your .p12 certificate file and enter the password
- For new certificate: Click **Generate Certificate**, enter the required details, and set a password

### STEP 6: Generate Installation Files
- [ ] Click the **Generate Installation Files** button
- [ ] Wait for completion
- [ ] Note the output directory path shown in the success message

### STEP 7: Access Generated Files
- Navigate to the output directory (typically PROJECT/BASEURL)
- You'll find the main installation scripts, configuration files, and helper directories

## Additional Features

### Component Version Override
- Enable **Version Override** to specify different versions for each component
- Enter custom version numbers as needed

### Detection Settings
- Click **Detection Settings** to configure store/workstation detection
- Set the base directory for station files
- Configure component-specific detection files

### Create Offline Package
- Click **Create Offline Package** for installations without internet access
- Select components and dependencies to include
- Configure WebDAV connection for downloading files

### Launcher Settings
- Click **Launcher Settings Editor** for advanced configuration
- Customize port settings and installation options
- Save your custom launcher settings

### KeePass Integration
- Click **KeePass Connect** if you use Pleasant Password Server
- Enter the KeePass server URL and credentials
- Select the appropriate project/folder when prompted

## After Initial Setup
- On subsequent launches, the application will display all sections at once
- Your previous configuration will be loaded automatically

## Next Steps
- Transfer the generated installation files to the target system
- Run the appropriate installation script (GKInstall.ps1 for Windows, GKInstall.sh for Linux) 
