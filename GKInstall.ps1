param(
    [switch]$offline,
    [ValidateSet('POS', 'WDM')]
    [string]$ComponentType = 'POS',
    [string]$base_url = "test.cse.cloud4retail.co"
)

# Stop on first error
$ErrorActionPreference = "Stop"

# Function for error handling
function Handle-Error {
    param($LineNumber)
    Write-Host "Error occurred at line $LineNumber"
    exit 1
}

# Function to get JRE version from filename
function Get-JreVersion {
    param($JreZip)
    # Extract version from filename (assuming format jre-VERSION.zip)
    $version = [System.IO.Path]::GetFileNameWithoutExtension($JreZip) -replace 'jre-',''
    if ([string]::IsNullOrEmpty($version)) {
        Write-Host "Error: Could not extract JRE version from filename $JreZip"
        return $null
    }
    return $version
}

# Function to get Tomcat version from filename
function Get-TomcatVersion {
    param($TomcatZip)
    # Extract version from filename (assuming format tomcat-VERSION.zip)
    $version = [System.IO.Path]::GetFileNameWithoutExtension($TomcatZip) -replace 'tomcat-',''
    if ([string]::IsNullOrEmpty($version)) {
        Write-Host "Error: Could not extract Tomcat version from filename $TomcatZip"
        return $null
    }
    return $version
}

# Update these lines to use the base_url
$server = $base_url
$dsg_server = $base_url

# Basic configuration
$version = "v1.0.0"
$base_install_dir = "C:\gkretail"

# Set component-specific configurations
$systemType = if ($ComponentType -eq 'POS') { "GKR-OPOS-CLOUD" } else { "CSE-wdm" }
$install_dir = Join-Path $base_install_dir $(if ($ComponentType -eq 'POS') { "pos-full" } else { "wdm" })

# Initialize offline variables
$jre_version = ""
$jre_file = ""
$tomcat_version = ""
$tomcat_file = ""

# Set WDM SSL settings based on base install directory
$security_dir = Join-Path $base_install_dir "security"
$ssl_path = Join-Path $security_dir "cse_wdm.p12"
$ssl_password = "changeit"

# Check offline mode
$offline_mode = $offline.IsPresent

# Validate WDM-specific parameters
if ($ComponentType -eq 'WDM') {
    if ([string]::IsNullOrEmpty($ssl_path)) {
        Write-Host "Error: ssl_path is required for WDM installation"
        exit 1
    }
    if ([string]::IsNullOrEmpty($ssl_password)) {
        Write-Host "Error: ssl_password is required for WDM installation"
        exit 1
    }
}

# Add component-specific package directory check
$package_dir = if ($ComponentType -eq 'POS') { "offline_package_POS" } else { "offline_package_WDM" }

# Update offline mode checks
if ($offline.IsPresent) {
    # Check for component-specific offline package
    if (-not (Test-Path $package_dir)) {
        Write-Host "Error: Offline package directory not found: $package_dir"
        exit 1
    }

    # Check for required files based on component type
    if ($ComponentType -eq 'WDM') {
        $required_files = @(
            (Join-Path $package_dir "Launcher.exe"),
            (Join-Path $package_dir "jre-11.0.20.zip"),
            (Join-Path $package_dir "tomcat-9.0.78.zip")
        )
    } else {
        $required_files = @(
            (Join-Path $package_dir "Launcher.exe")
        )
    }

    foreach ($file in $required_files) {
        if (-not (Test-Path $file)) {
            Write-Host "Error: Required file not found: $file"
            exit 1
        }
    }

    # Update file paths to use component-specific directory
    $launcher_path = Join-Path $package_dir "Launcher.exe"
    if ($ComponentType -eq 'WDM') {
        $jre_file = Join-Path $package_dir "jre-11.0.20.zip"
        $tomcat_file = Join-Path $package_dir "tomcat-9.0.78.zip"
    }
}

# Create installation directory if it doesn't exist
if (-not (Test-Path $install_dir)) {
    New-Item -ItemType Directory -Path $install_dir -Force
}

# Get hostname
$hs = $env:COMPUTERNAME
if ([string]::IsNullOrEmpty($hs)) {
    Write-Host "Warning: Could not read hostname. Falling back to manual input."
} else {
    Write-Host "-------------------"
    Write-Host "Hostname  : $hs"
    Write-Host "==================="
    $hostname = $hs
}

# Try to extract parts from hostname first
try {
    if ([string]::IsNullOrEmpty($hs)) { throw "No hostname available" }
    
    $part1 = $hostname.Substring(0,2)   # Country
    $part3 = $hostname.Substring(8,1)   # Test/Prod flag
    $part5 = $hostname.Substring(13,3)  # POS number

    # Validate extracted parts
    if ($part1 -notmatch '^[A-Z]{2}$') { throw "Invalid country code" }
    if ($part3 -notmatch '^[TP]$') { throw "Invalid environment" }
    if ($part5 -notmatch '^\d{3}$') { throw "Invalid POS number" }

    Write-Host "Successfully detected values from hostname:"
    Write-Host "Country: $part1"
    Write-Host "Environment: $part3"
    Write-Host "POS Number: $part5"
}
catch {
    Write-Host "Could not extract valid values from hostname. Falling back to manual input."
    
    do {
        $part1 = Read-Host "Please enter the Country Code (2 letters)"
    } while ($part1 -notmatch '^[A-Z]{2}$')

    do {
        $part3 = Read-Host "Please enter the Environment (T for Test, P for Production)"
    } while ($part3 -notmatch '^[TP]$')

    do {
        $part5 = Read-Host "Please enter the POS Number (3 digits)"
    } while ($part5 -notmatch '^\d{3}$')
}

# Always prompt for Store Number
do {
    $part4 = Read-Host "Please enter the Store Number (4 digits)"
} while ($part4 -notmatch '^\d{4}$')

# Print final results
Write-Host "-------------------"
Write-Host "Country   : $part1"
Write-Host "Environment: $part3"
Write-Host "StoreNr   : $part4"
Write-Host "PosNr     : $part5"
Write-Host "-------------------"

# Define system types
$systemTypes = @{
    POS = "GKR-OPOS-CLOUD"
    WDM = "CSE-wdm"
    # Add other components here as needed
}

# Get the system type based on component type
$systemType = $systemTypes[$ComponentType]

# After the basic configuration section, update the onboarding call
Write-Host "Starting onboarding process for $ComponentType"

# Call the onboarding script with the appropriate component type
try {
    .\onboarding.ps1 -ComponentType $ComponentType
    Write-Host "$ComponentType onboarding completed successfully"
}
catch {
    Write-Host "Error during $ComponentType onboarding: $_"
    exit 1
}

# Read onboarding token
$onboardingTokenPath = "onboarding.token"
if (-not (Test-Path $onboardingTokenPath)) {
    Write-Host "Error: Onboarding token file not found at: $onboardingTokenPath"
    exit 1
}
$onboardingToken = Get-Content -Path $onboardingTokenPath -Raw
$onboardingToken = $onboardingToken.Trim()

# Create configuration files
$installationToken = @"
configService.url=https://@Server@/config-service
cims.url=https://@Server@/cims
station.tenantId=001
station.storeId=@StoreNr@
station.workstationId=@PosNr@
station.applicationVersion=@Version@
station.systemType=$systemType
onboarding.token=$onboardingToken
dsg.url=https://@DsgServer@/dsg/content/cep/SoftwarePackage
"@

$installationToken = $installationToken.Replace("@Country@", $part1)
$installationToken = $installationToken.Replace("@StoreNr@", $part4)
$installationToken = $installationToken.Replace("@PosNr@", $part5)
$installationToken = $installationToken.Replace("@Version@", $version)
$installationToken = $installationToken.Replace("@Server@", $server)
$installationToken = $installationToken.Replace("@DsgServer@", $dsg_server)

Set-Content -Path "installationtoken.txt" -Value $installationToken

# Create base64 token
$bytes = [System.Text.Encoding]::UTF8.GetBytes($installationToken)
$base64Token = [Convert]::ToBase64String($bytes)
Set-Content -Path "installationtoken.base64" -Value $base64Token

# Create addonpack.properties
$addonpackProps = @"
dsg.addonpack.url=https://$dsg_server/dsg/content/cep/AddOnPacks
addonpacks=
"@
Set-Content -Path "$install_dir\addonpack.properties" -Value $addonpackProps

# Handle .p12 file if it exists
$p12Files = Get-ChildItem -Path "." -Filter "*.p12"
if ($p12Files.Count -gt 0) {
    Write-Host "Found .p12 file(s) in script directory"
    
    # Create security directory if it doesn't exist
    if (-not (Test-Path $security_dir)) {
        Write-Host "Creating security directory: $security_dir"
        New-Item -ItemType Directory -Path $security_dir -Force | Out-Null
    }
    
    # Copy each .p12 file found
    foreach ($p12File in $p12Files) {
        if ($ComponentType -eq 'WDM') {
            # For WDM, always use the standard filename
            $destPath = Join-Path $security_dir "cse_wdm.p12"
            Write-Host "Copying $($p12File.Name) to $destPath as cse_wdm.p12"
        } else {
            # For other components, keep original filename
            $destPath = Join-Path $security_dir $p12File.Name
            Write-Host "Copying $($p12File.Name) to $destPath"
        }
        Copy-Item -Path $p12File.FullName -Destination $destPath -Force
    }
}

# Paths
$launchersPath = Join-Path $PSScriptRoot "helper\launchers"

# Verify launchers path exists
if (-Not (Test-Path $launchersPath)) {
    Write-Host "Launchers path does not exist: $launchersPath"
    exit
}

# Select the appropriate template file
$templateFile = if ($ComponentType -eq 'POS') { 
    Join-Path $launchersPath "launcher.pos.template" 
} else { 
    Join-Path $launchersPath "launcher.wdm.template" 
}

if (-not (Test-Path $templateFile)) {
    Write-Host "Error: Template file $templateFile not found"
    exit 1
}

# Read the template content
$launcherProps = Get-Content -Path $templateFile -Raw

# Replace placeholders with actual values
$replacements = @{
    '@INSTALL_DIR@' = $install_dir
    '@BASE64_TOKEN@' = $base64Token
    '@OFFLINE_MODE@' = $(if ($offline_mode) { "1" } else { "0" })
    '@JRE_VERSION@' = $(if ($offline_mode) { $jre_version } else { "" })
    '@JRE_PACKAGE@' = $(if ($offline_mode) { "$PWD\offline_package\jre-$jre_version.zip" } else { "" })
    '@INSTALLER_PACKAGE@' = $(if ($offline_mode) { "$PWD\offline_package\installer.jar" } else { "" })
}

if ($ComponentType -eq 'WDM') {
    $replacements['@SSL_PATH@'] = $ssl_path
    $replacements['@SSL_PASSWORD@'] = $ssl_password
    $replacements['@TOMCAT_VERSION@'] = $(if ($offline_mode) { $tomcat_version } else { "" })
    $replacements['@TOMCAT_PACKAGE@'] = $(if ($offline_mode) { "$PWD\offline_package\tomcat-$tomcat_version.zip" } else { "" })
}

# Apply all replacements
foreach ($key in $replacements.Keys) {
    $launcherProps = $launcherProps.Replace($key, $replacements[$key])
}

Write-Host "Writing launcher properties to file..."
Set-Content -Path "launcher.properties" -Value $launcherProps
Get-Content -Path "launcher.properties" | Write-Host

# Download or use local Launcher
if (-not $offline_mode) {
    $download_url = "https://$base_url/dsg/content/cep/SoftwarePackage/$systemType/$version/Launcher.exe"
    Write-Host "Attempting to download Launcher.exe from: $download_url"
    try {
        Invoke-WebRequest -Uri $download_url -OutFile "Launcher.exe"
        Write-Host "Successfully downloaded Launcher.exe"
    }
    catch {
        Write-Host "Error downloading Launcher.exe: $_"
        exit 1
    }
}

# Start the installation
Write-Host "Starting installation..."
Write-Host "Running Launcher with arguments: --defaultsFile launcher.properties --mode unattended"

# Start Launcher without waiting
$launcherProcess = Start-Process -FilePath ".\Launcher.exe" -ArgumentList "--defaultsFile", "launcher.properties", "--mode", "unattended" -PassThru

# Check installation logs
$installerLogPath = Join-Path $install_dir "installer\log\installer.log"
$maxWaitTime = 1800 # 30 minutes timeout
$maxLogWaitTime = 300 # 5 minutes timeout for log file creation
$elapsed = 0
$logWaitElapsed = 0
$checkInterval = 2 # Check every 2 seconds
$lastLineNumber = 0
$firstLog = $true

Write-Host "Waiting for installation to complete..."
Write-Host "Monitoring log: $installerLogPath"

while ($elapsed -lt $maxWaitTime) {
    # Check if launcher is still running
    if ($launcherProcess.HasExited) {
        Write-Host "Launcher process has exited with code: $($launcherProcess.ExitCode)"
        Write-Host "Continuing to monitor logs for 30 seconds..."
        
        $postExitTime = 30
        while ($postExitTime -gt 0) {
            if (Test-Path $installerLogPath) {
                try {
                    # Read new lines from the log
                    $currentContent = Get-Content $installerLogPath -ErrorAction Stop
                    
                    if ($currentContent.Count -gt $lastLineNumber) {
                        $newLines = $currentContent[$lastLineNumber..($currentContent.Count-1)]
                        foreach ($line in $newLines) {
                            Write-Host "LOG: $line"
                        }
                        $lastLineNumber = $currentContent.Count
                    }
                }
                catch {
                    Write-Host "Error reading log file: $_"
                }
            }
            
            Write-Host -NoNewline "`rTime remaining for log monitoring: $postExitTime seconds..."
            Start-Sleep -Seconds 1
            $postExitTime--
        }
        Write-Host "`nCompleting installation..."
        
        # Final log check
        if (Test-Path $installerLogPath) {
            try {
                $finalLogContent = Get-Content $installerLogPath -ErrorAction Stop | Select-Object -Last 20
                if ($finalLogContent -match "Installation finished successfully") {
                    Write-Host "Installation completed successfully!"
                    Write-Host "Installation directory: $install_dir"
                    if ($ComponentType -eq 'WDM') {
                        Write-Host "WDM installation completed. Please check the following:"
                        Write-Host "1. Tomcat service status"
                        Write-Host "2. WDM application accessibility at https://localhost:8543"
                    } else {
                        Write-Host "POS installation completed. Please check the POS application status."
                    }
                    exit 0
                }
                elseif ($finalLogContent -match "Installation failed") {
                    Write-Host "Installation failed. Please check the logs at: $installerLogPath"
                    exit 1
                }
            }
            catch {
                Write-Host "Error reading final log state: $_"
            }
        }
        
        # If we couldn't determine status from logs, use process exit code
        if ($launcherProcess.ExitCode -eq 0) {
            Write-Host "Launcher completed successfully based on exit code."
            Write-Host "Installation directory: $install_dir"
            exit 0
        } else {
            Write-Host "Launcher failed with exit code: $($launcherProcess.ExitCode)"
            Write-Host "Please check the logs at: $installerLogPath"
            exit 1
        }
    }

    if (Test-Path $installerLogPath) {
        try {
            # First time we see the log file
            if ($firstLog) {
                Write-Host "Log file created at: $installerLogPath"
                $firstLog = $false
            }

            # Read new lines from the log
            $currentContent = Get-Content $installerLogPath -ErrorAction Stop
            
            if ($currentContent.Count -gt $lastLineNumber) {
                $newLines = $currentContent[$lastLineNumber..($currentContent.Count-1)]
                foreach ($line in $newLines) {
                    Write-Host "LOG: $line"
                }
                $lastLineNumber = $currentContent.Count
            }

            # Check for completion
            $logContent = $currentContent | Select-Object -Last 20
            if ($logContent -match "Installation finished successfully") {
                Write-Host "Installation completed successfully!"
                Write-Host "Installation directory: $install_dir"
                if ($ComponentType -eq 'WDM') {
                    Write-Host "WDM installation completed. Please check the following:"
                    Write-Host "1. Tomcat service status"
                    Write-Host "2. WDM application accessibility at https://localhost:8543"
                } else {
                    Write-Host "POS installation completed. Please check the POS application status."
                }
                exit 0
            }
            elseif ($logContent -match "Installation failed") {
                Write-Host "Installation failed. Please check the logs at: $installerLogPath"
                exit 1
            }
        }
        catch {
            Write-Host "Error reading log file: $_"
        }
    } else {
        Write-Host "Waiting for installer log file to be created... ($logWaitElapsed seconds elapsed)"
        $logWaitElapsed += $checkInterval
        if ($logWaitElapsed -ge $maxLogWaitTime) {
            Write-Host "Error: Timeout waiting for installer log file to be created after $($maxLogWaitTime/60) minutes"
            Write-Host "Expected log path: $installerLogPath"
            # Try to kill launcher process if it's still running
            if (-not $launcherProcess.HasExited) {
                Write-Host "Terminating launcher process..."
                $launcherProcess.Kill()
            }
            exit 1
        }
    }
    
    Start-Sleep -Seconds $checkInterval
    $elapsed += $checkInterval
    
    # Show progress less frequently
    if ($elapsed % 30 -eq 0) {
        Write-Host "Installation in progress... ($(${elapsed}/60) minutes elapsed)"
    }
}

# Try to kill launcher process if it's still running after timeout
if (-not $launcherProcess.HasExited) {
    Write-Host "Terminating launcher process due to timeout..."
    $launcherProcess.Kill()
}

Write-Host "Warning: Installation timeout reached after 30 minutes. Please check the installation logs at: $installerLogPath"
Write-Host "Installation directory: $install_dir"
exit 1 