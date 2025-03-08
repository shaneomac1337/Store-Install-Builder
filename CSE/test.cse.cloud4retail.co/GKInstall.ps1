param(
    [switch]$offline,
    [ValidateSet('POS', 'WDM', 'FLOW-SERVICE', 'LPA', 'SH', 'LPA-SERVICE', 'STOREHUB-SERVICE')]
    [string]$ComponentType = 'POS',
    [string]$base_url = "test.cse.cloud4retail.co"
)

# Stop on first error
$ErrorActionPreference = "Stop"

# Map shortened component types to full names
if ($ComponentType -eq 'LPA') {
    $ComponentType = 'LPA-SERVICE'
} elseif ($ComponentType -eq 'SH') {
    $ComponentType = 'STOREHUB-SERVICE'
}

# Function for error handling
function Handle-Error {
    param($LineNumber)
    Write-Host "Error occurred at line $LineNumber"
    exit 1
}

# Function to extract version from any package filename
function Get-PackageVersion {
    param(
        [string]$PackageFile,
        [string]$ComponentPrefix
    )
    
    # Get filename without extension
    $filename = [System.IO.Path]::GetFileNameWithoutExtension($PackageFile)
    
    # Try different patterns to extract version
    
    # Pattern 1: prefix-1.2.3 (standard format)
    if ($filename -match "^$ComponentPrefix-(\d+(\.\d+)*)$") {
        return $matches[1]
    }
    
    # Pattern 2: prefix-1.2.3-suffix (with additional info)
    if ($filename -match "^$ComponentPrefix-(\d+(\.\d+)*)-") {
        return $matches[1]
    }
    
    # Pattern 3: prefix_1_2_3 (underscore format)
    if ($filename -match "^$ComponentPrefix[_-](\d+)[_\.](\d+)[_\.](\d+)") {
        return "$($matches[1]).$($matches[2]).$($matches[3])"
    }
    
    # Pattern 4: prefix1.2.3 (no separator)
    if ($filename -match "^$ComponentPrefix(\d+(\.\d+)*)$") {
        return $matches[1]
    }
    
    # Pattern 5: just extract any sequence of numbers and dots
    if ($filename -match '(\d+(\.\d+)*)') {
        return $matches[1]
    }
    
    # If no pattern matches, return the original filename without prefix
    $version = $filename -replace "^$ComponentPrefix-",''
    if ([string]::IsNullOrEmpty($version)) {
        Write-Host "Error: Could not extract version from filename $PackageFile"
        return $null
    }
    return $version
}

# Function to get JRE version from filename
function Get-JreVersion {
    param($JreZip)
    
    # Get filename without extension
    $filename = [System.IO.Path]::GetFileNameWithoutExtension($JreZip)
    
    # Special case for Java_zulujre pattern
    if ($filename -match "Java_zulujre.*?[-_](\d+\.\d+\.\d+)") {
        Write-Host "Detected Java version $($matches[1]) from Zulu JRE filename"
        return $matches[1]
    }
    
    # Special case for x64/x86 in filename to avoid extracting "64" as version
    if ($filename -match "x64-(\d+\.\d+\.\d+)") {
        Write-Host "Detected Java version $($matches[1]) from x64 pattern"
        return $matches[1]
    }
    if ($filename -match "x86-(\d+\.\d+\.\d+)") {
        Write-Host "Detected Java version $($matches[1]) from x86 pattern"
        return $matches[1]
    }
    
    # Try jre prefix first, then java if that fails
    $version = Get-PackageVersion -PackageFile $JreZip -ComponentPrefix "jre"
    if ([string]::IsNullOrEmpty($version)) {
        $version = Get-PackageVersion -PackageFile $JreZip -ComponentPrefix "java"
    }
    
    # Validate version format - if it's just a number like "64", it's probably wrong
    if ($version -match "^\d+$" -and $filename -match "(\d+\.\d+\.\d+)") {
        # Extract version with format like 11.0.18
        Write-Host "Correcting invalid version '$version' to $($matches[1])"
        return $matches[1]
    }
    
    return $version
}

# Function to get Tomcat version from filename
function Get-TomcatVersion {
    param($TomcatZip)
    return Get-PackageVersion -PackageFile $TomcatZip -ComponentPrefix "tomcat"
}

# Update these lines to use the base_url
$server = $base_url
$dsg_server = $base_url

# Basic configuration

# Component-specific versions
$use_version_override = $false
$pos_version = "v1.0.0"
$wdm_version = "v1.0.0"
$flow_service_version = "v1.0.0"
$lpa_service_version = "v1.0.0"
$storehub_service_version = "v1.0.0"

# Function to get the correct version based on system type
function Get-ComponentVersion {
    param($SystemType)
    
    # If version override is disabled, always use the default version
    if (-not $use_version_override) {
        return $version
    }
    
    # If the system type doesn't have a specific version pattern, use the default version
    if (-not $SystemType -or $SystemType -eq "") {
        return $version
    }
    
    switch ($SystemType) {
        # POS components
        "CSE-OPOS-CLOUD" { return $pos_version }
        
        # WDM components
        "CSE-wdm" { return $wdm_version }
        
        # Flow Service components
        "GKR-FLOWSERVICE-CLOUD" { return $flow_service_version }
        
        # LPA Service components
        "CSE-lps-lpa" { return $lpa_service_version }
        
        # StoreHub Service components
        "CSE-sh-cloud" { return $storehub_service_version }
        
        # For any other system type, use the project version
        default { return $version }
    }
}

# Note: This script will use the certificate generated by the GK Install Builder
# The certificate is located in the security directory

$version = "v1.0.0"
$base_install_dir = "C:\gkretail"

# Set component-specific configurations
$systemType = switch ($ComponentType) {
    'POS' { "CSE-OPOS-CLOUD" }
    'WDM' { "CSE-wdm" }
    'FLOW-SERVICE' { "GKR-FLOWSERVICE-CLOUD" }
    'LPA-SERVICE' { "CSE-lps-lpa" }
    'STOREHUB-SERVICE' { "CSE-sh-cloud" }
    default { "CSE-OPOS-CLOUD" }
}
$install_dir = Join-Path $base_install_dir $(
    if ($ComponentType -eq 'POS') { "pos-full" } 
    elseif ($ComponentType -eq 'WDM') { "wdm" }
    elseif ($ComponentType -eq 'FLOW-SERVICE') { "flow-service" }
    elseif ($ComponentType -eq 'LPA-SERVICE') { "lpa-service" }
    elseif ($ComponentType -eq 'STOREHUB-SERVICE') { "storehub-service" }
    else { "wdm" }
)

# Initialize offline variables
$jre_version = ""
$jre_file = ""
$tomcat_version = ""
$tomcat_file = ""

# Set WDM SSL settings based on base install directory
$security_dir = Join-Path $base_install_dir "security"
# We'll find the actual certificate file dynamically later
$ssl_password = "changeit"

# Check offline mode
$offline_mode = $offline.IsPresent

# Validate WDM-specific parameters
if ($ComponentType -eq 'WDM') {
    if ([string]::IsNullOrEmpty($ssl_password)) {
        Write-Host "Error: ssl_password is required for WDM installation"
        exit 1
    }
}

# Add component-specific package directory check
$package_dir = if ($ComponentType -eq 'LPA-SERVICE') { "offline_package_LPA" }
               elseif ($ComponentType -eq 'STOREHUB-SERVICE') { "offline_package_SH" }
               else { "offline_package_$ComponentType" }

# Update offline mode checks
if ($offline.IsPresent) {
    # Check for component-specific offline package
    if (-not (Test-Path $package_dir)) {
        Write-Host "Error: Offline package directory not found: $package_dir"
        exit 1
    }

    # Check for required files based on component type
    if ($ComponentType -eq 'WDM') {
        # Find JRE and Tomcat packages dynamically with more flexible patterns
        $jre_files = @(Get-ChildItem -Path (Join-Path $package_dir "jre-*.zip") -ErrorAction SilentlyContinue)
        
        # If no jre files found, try java pattern
        if ($jre_files.Count -eq 0) {
            $jre_files = @(Get-ChildItem -Path (Join-Path $package_dir "java-*.zip") -ErrorAction SilentlyContinue)
        }
        
        # If still no files found, try a more generic pattern
        if ($jre_files.Count -eq 0) {
            $jre_files = @(Get-ChildItem -Path (Join-Path $package_dir "*jre*.zip") -ErrorAction SilentlyContinue)
            if ($jre_files.Count -eq 0) {
                $jre_files = @(Get-ChildItem -Path (Join-Path $package_dir "*java*.zip") -ErrorAction SilentlyContinue)
            }
        }
        
        $tomcat_files = @(Get-ChildItem -Path (Join-Path $package_dir "tomcat-*.zip") -ErrorAction SilentlyContinue)
        
        # If no tomcat files found, try a more generic pattern
        if ($tomcat_files.Count -eq 0) {
            $tomcat_files = @(Get-ChildItem -Path (Join-Path $package_dir "*tomcat*.zip") -ErrorAction SilentlyContinue)
        }
        
        # Look for any JAR file to use as installer
        $jar_files = @(Get-ChildItem -Path (Join-Path $package_dir "*.jar") -ErrorAction SilentlyContinue)
        $installer_jar = $null
        $has_installer_jar = $false
        
        if ($jar_files.Count -gt 0) {
            if ($jar_files.Count -gt 1) {
                Write-Host "Warning: Multiple JAR files found in $package_dir. Using the first one: $($jar_files[0].Name)"
            }
            $installer_jar = $jar_files[0].FullName
            $has_installer_jar = $true
            Write-Host "Found installer JAR: $($jar_files[0].Name)"
        }
        
        if ($jre_files.Count -eq 0) {
            Write-Host "Error: No JRE/Java package found in $package_dir"
            exit 1
        }
        
        if ($tomcat_files.Count -eq 0) {
            Write-Host "Error: No Tomcat package found in $package_dir"
            exit 1
        }
        
        # Use the first matching file if multiple are found
        $jre_file = $jre_files[0].FullName
        $tomcat_file = $tomcat_files[0].FullName
        
        # Extract versions
        $jre_version = Get-JreVersion -JreZip $jre_files[0].Name
        $tomcat_version = Get-TomcatVersion -TomcatZip $tomcat_files[0].Name
        
        Write-Host "Found JRE/Java package: $($jre_files[0].Name), version: $jre_version"
        Write-Host "Found Tomcat package: $($tomcat_files[0].Name), version: $tomcat_version"
        
        $required_files = @(
            (Join-Path $package_dir "Launcher.exe"),
            $jre_file,
            $tomcat_file
        )
        
        # Add installer.jar to required files if it exists
        if ($has_installer_jar) {
            $required_files += $installer_jar
        }
    } else {
        # For other components - generic approach with improved detection
        # Find JRE and Tomcat packages dynamically with more flexible patterns
        $jre_files = @(Get-ChildItem -Path (Join-Path $package_dir "jre-*.zip") -ErrorAction SilentlyContinue)
        
        # If no jre files found, try java pattern
        if ($jre_files.Count -eq 0) {
            $jre_files = @(Get-ChildItem -Path (Join-Path $package_dir "java-*.zip") -ErrorAction SilentlyContinue)
        }
        
        # If still no files found, try a more generic pattern
        if ($jre_files.Count -eq 0) {
            $jre_files = @(Get-ChildItem -Path (Join-Path $package_dir "*jre*.zip") -ErrorAction SilentlyContinue)
            if ($jre_files.Count -eq 0) {
                $jre_files = @(Get-ChildItem -Path (Join-Path $package_dir "*java*.zip") -ErrorAction SilentlyContinue)
            }
        }
        
        $tomcat_files = @(Get-ChildItem -Path (Join-Path $package_dir "tomcat-*.zip") -ErrorAction SilentlyContinue)
        
        # If no tomcat files found, try a more generic pattern
        if ($tomcat_files.Count -eq 0) {
            $tomcat_files = @(Get-ChildItem -Path (Join-Path $package_dir "*tomcat*.zip") -ErrorAction SilentlyContinue)
        }
        
        # Look for any JAR file to use as installer
        $jar_files = @(Get-ChildItem -Path (Join-Path $package_dir "*.jar") -ErrorAction SilentlyContinue)
        $installer_jar = $null
        $has_installer_jar = $false
        
        if ($jar_files.Count -gt 0) {
            if ($jar_files.Count -gt 1) {
                Write-Host "Warning: Multiple JAR files found in $package_dir. Using the first one: $($jar_files[0].Name)"
            }
            $installer_jar = $jar_files[0].FullName
            $has_installer_jar = $true
            Write-Host "Found installer JAR: $($jar_files[0].Name)"
        }
        
        # Initialize required files with Launcher.exe
        $required_files = @(
            (Join-Path $package_dir "Launcher.exe")
        )
        
        # Process JRE files if available
        if ($jre_files.Count -gt 0) {
            $jre_file = $jre_files[0].FullName
            $jre_version = Get-JreVersion -JreZip $jre_files[0].Name
            Write-Host "Found JRE/Java package: $($jre_files[0].Name), version: $jre_version"
            $required_files += $jre_file
        } else {
            Write-Host "No JRE/Java package found for $ComponentType."
        }
        
        # Process Tomcat files if available
        if ($tomcat_files.Count -gt 0) {
            $tomcat_file = $tomcat_files[0].FullName
            $tomcat_version = Get-TomcatVersion -TomcatZip $tomcat_files[0].Name
            Write-Host "Found Tomcat package: $($tomcat_files[0].Name), version: $tomcat_version"
            $required_files += $tomcat_file
        } else {
            Write-Host "No Tomcat package found for $ComponentType."
        }
        
        # Add installer.jar to required files if it exists
        if ($has_installer_jar) {
            $required_files += $installer_jar
        }
    }

    foreach ($file in $required_files) {
        if (-not (Test-Path $file)) {
            Write-Host "Error: Required file not found: $file"
            exit 1
        }
    }

    # Update file paths to use component-specific directory
    $launcher_path = Join-Path $package_dir "Launcher.exe"
    # JRE and Tomcat files are already set in the dynamic detection code above
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

# Create security directory if it doesn't exist
if (-not (Test-Path $security_dir)) {
    Write-Host "Creating security directory: $security_dir"
    New-Item -ItemType Directory -Path $security_dir -Force | Out-Null
}

# Check for certificates in the security directory
$securityP12Files = Get-ChildItem -Path $security_dir -Filter "*.p12" -ErrorAction SilentlyContinue
$ssl_path = $null

if ($securityP12Files.Count -gt 0) {
    # Use the first .p12 file found in the security directory
    $ssl_path = $securityP12Files[0].FullName
    Write-Host "Found certificate at: $ssl_path"
} else {
    # Check for .p12 files in the current directory
    if ($p12Files.Count -gt 0) {
        Write-Host "Found .p12 file(s) in script directory"
        
        # Copy each .p12 file found
        foreach ($p12File in $p12Files) {
            # Copy with original filename
            $destPath = Join-Path $security_dir $p12File.Name
            Write-Host "Copying $($p12File.Name) to $destPath"
            Copy-Item -Path $p12File.FullName -Destination $destPath -Force
            
            # Set the ssl_path to the first certificate copied
            if ($null -eq $ssl_path) {
                $ssl_path = $destPath
            }
        }
    } else {
        # No certificate found
        Write-Host "Warning: No certificate found for WDM. The installation may fail if a certificate is required."
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
} elseif ($ComponentType -eq 'WDM') {
    Join-Path $launchersPath "launcher.wdm.template"
} elseif ($ComponentType -eq 'FLOW-SERVICE') {
    Join-Path $launchersPath "launcher.flow-service.template"
} elseif ($ComponentType -eq 'LPA-SERVICE') {
    Join-Path $launchersPath "launcher.lpa-service.template"
} elseif ($ComponentType -eq 'STOREHUB-SERVICE') {
    Join-Path $launchersPath "launcher.storehub-service.template"
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
    '@JRE_VERSION@' = $(if ($offline_mode -and -not [string]::IsNullOrEmpty($jre_version)) { $jre_version } else { "" })
    '@JRE_PACKAGE@' = $(if ($offline_mode -and $jre_files.Count -gt 0) { "$PWD\$package_dir\$($jre_files[0].Name)" } else { "" })
    '@INSTALLER_PACKAGE@' = $(if ($offline_mode -and $has_installer_jar) { $installer_jar } else { "" })
    '@SSL_PATH@' = $ssl_path
    '@SSL_PASSWORD@' = $ssl_password
    'localhost' = $(if ($ComponentType -eq 'STOREHUB-SERVICE') { "localhost" } else { "" })
}

# Add Tomcat replacements if Tomcat files were found
if ($tomcat_files.Count -gt 0) {
    $replacements['@TOMCAT_VERSION@'] = $(if ($offline_mode) { $tomcat_version } else { "" })
    $replacements['@TOMCAT_PACKAGE@'] = $(if ($offline_mode) { "$PWD\$package_dir\$($tomcat_files[0].Name)" } else { "" })
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
    $component_version = Get-ComponentVersion -SystemType $systemType
# If the component version is empty or null, fall back to the default version
if ([string]::IsNullOrEmpty($component_version)) {
    $component_version = $version
}
$download_url = "https://$base_url/dsg/content/cep/SoftwarePackage/$systemType/$component_version/Launcher.exe"
    Write-Host "Attempting to download Launcher.exe from: $download_url"
    try {
        Invoke-WebRequest -Uri $download_url -OutFile "Launcher.exe"
        Write-Host "Successfully downloaded Launcher.exe"
    }
    catch {
        Write-Host "Error downloading Launcher.exe: $_"
        exit 1
    }
} else {
    # In offline mode, copy the Launcher.exe from the package directory to the current directory
    Write-Host "Copying Launcher.exe from $package_dir to current directory..."
    try {
        Copy-Item -Path $launcher_path -Destination ".\Launcher.exe" -Force
        Write-Host "Successfully copied Launcher.exe"
    }
    catch {
        Write-Host "Error copying Launcher.exe: $_"
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
                    
                    # Component-specific completion messages
                    if ($ComponentType -eq 'WDM') {
                        Write-Host "WDM installation completed. Please check the following:"
                        Write-Host "1. Tomcat service status"
                        Write-Host "2. WDM application accessibility at https://localhost:8543"
                    } else {
                        Write-Host "$ComponentType installation completed. Please check the application status."
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
                
                # Component-specific completion messages
                if ($ComponentType -eq 'WDM') {
                    Write-Host "WDM installation completed. Please check the following:"
                    Write-Host "1. Tomcat service status"
                    Write-Host "2. WDM application accessibility at https://localhost:8543"
                } else {
                    Write-Host "$ComponentType installation completed. Please check the application status."
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