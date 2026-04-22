<#
.SYNOPSIS
    Coop Sweden WDM Installation Wrapper with Service Management
.DESCRIPTION
    All-in-one wrapper that:
    1. Requests administrator privileges for service management
    2. Stops TomcatWDMMonitor service
    3. Terminates processes on port 8080 (Tomcat) and port 4333 (application)
    4. Waits for TCP connections to clear
    5. Creates timestamped backup of existing WDM installation
    6. Cleans WDM directory for fresh install
    7. Runs GKInstall.ps1 as normal user (non-elevated)
    8. Waits for installation to complete
    9. Restarts TomcatWDMMonitor service

    This ensures the installation runs without admin privileges while
    still managing the Windows service that requires elevation.
.PARAMETER VersionOverride
    Optional. Forwarded to GKInstall.ps1 to pin the WDM component version
    (e.g. v5.27.1 or 5.27.1). When omitted, GKInstall.ps1 uses its configured
    default/source.
.PARAMETER SkipStoreInit
    Optional. Forwarded to GKInstall.ps1 to bypass the store initialization
    step after onboarding. Edge-case use only (e.g. backend already has the
    workstation and store-init would otherwise fail).
.EXAMPLE
    .\InstallWDM_legacy.ps1
.EXAMPLE
    .\InstallWDM_legacy.ps1 -VersionOverride v5.27.1
.EXAMPLE
    .\InstallWDM_legacy.ps1 -SkipStoreInit
#>
param(
    [string]$VersionOverride,
    [switch]$SkipStoreInit
)

# Self-elevate the script if required
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Requesting administrator privileges..." -ForegroundColor Yellow
    Write-Host "Please click 'Yes' in the UAC prompt to continue." -ForegroundColor Yellow
    Start-Sleep -Seconds 2

    # Relaunch as administrator with explicit directory change, forwarding parameters
    $scriptPath = $PSCommandPath
    $scriptDir = $PSScriptRoot
    $forwardedArgs = ""
    if ($PSBoundParameters.ContainsKey('VersionOverride') -and $VersionOverride) {
        $escapedVersion = $VersionOverride.Replace("'", "''")
        $forwardedArgs += " -VersionOverride '$escapedVersion'"
    }
    if ($SkipStoreInit) {
        $forwardedArgs += " -SkipStoreInit"
    }
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -Command `"Set-Location '$scriptDir'; & '$scriptPath'$forwardedArgs`"" -Verb RunAs
    exit
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Coop Sweden WDM Installation" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Running with administrator privileges for service management" -ForegroundColor Green
Write-Host ""

# WDM Installation Directory
$base_install_dir = "C:\gkretail"
$install_dir = Join-Path $base_install_dir "wdm"

# ============================================
# Helper Functions
# ============================================

# Function to check if a port is in use
function Test-PortInUse {
    param([int]$Port)

    # Use netstat method as primary approach
    try {
        $netstatOutput = netstat -ano | Select-String "LISTENING" | Select-String ":$Port "
        if ($netstatOutput) {
            Write-Host "Netstat detected service on port $Port"
            return $true
        }
    } catch {
        Write-Host ("Netstat port check method failed for port " + $Port + ": " + $_)
    }

    # Fallback to Get-NetTCPConnection method
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($connections.Count -gt 0) {
            Write-Host "Fallback method detected service on port $Port"
            return $true
        }
    } catch {
        Write-Host ("Fallback port check method failed for port " + $Port + ": " + $_)
    }

    # Try another approach to detect Java processes that might be Tomcat
    if ($Port -eq 8080) {
        $javaProcList = Get-Process -Name "java" -ErrorAction SilentlyContinue
        if ($javaProcList) {
            Write-Host "Found Java processes that could be Tomcat, assuming port 8080 is in use"
            return $true
        }
    }

    return $false
}

# Function to find process using a specific port
function Get-ProcessByPort {
    param([int]$Port)

    # Use netstat method as primary approach
    try {
        $netstatOutput = netstat -ano | Select-String "LISTENING" | Select-String ":$Port "
        if ($netstatOutput) {
            $pidMatches = $netstatOutput -match '\s+(\d+)$'
            if ($pidMatches) {
                $processPid = $matches[1]
                $process = Get-Process -Id $processPid -ErrorAction SilentlyContinue
                if ($process) {
                    Write-Host "Netstat method detected process $($process.Name) (PID: $processPid) on port $Port"
                    return $process
                }
            }
        }
    } catch {
        Write-Host ("Netstat process detection method failed for port " + $Port + ": " + $_)
    }

    # Fallback to Get-NetTCPConnection method
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($connections.Count -gt 0) {
            foreach ($conn in $connections) {
                $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
                if ($process) {
                    Write-Host "Fallback method detected process $($process.Name) (PID: $($process.Id)) on port $Port"
                    return $process
                }
            }
        }
    } catch {
        Write-Host ("Fallback process detection method failed for port " + $Port + ": " + $_)
    }

    # Special handling for Java/Tomcat detection
    if ($Port -eq 8080) {
        $javaProcList = Get-Process -Name "java" -ErrorAction SilentlyContinue
        if ($javaProcList) {
            Write-Host "Found Java process that could be Tomcat: $($javaProcList[0].Name) (PID: $($javaProcList[0].Id))"
            return $javaProcList[0]
        }
    }

    return $null
}

Write-Host "================================================================="
Write-Host "                   WDM PRE-INSTALLATION TASKS                    " -ForegroundColor Cyan
Write-Host "================================================================="

# ============================================
# Step 1: Stop TomcatWDMMonitor Service
# ============================================
Write-Host ""
Write-Host "=== Step 1: Stopping TomcatWDMMonitor Service ===" -ForegroundColor Cyan
$wdmMonitorServiceStopped = $false
try {
    $wdmMonitorService = Get-Service -Name "TomcatWDMMonitor" -ErrorAction SilentlyContinue
    if ($wdmMonitorService) {
        Write-Host "Found TomcatWDMMonitor service (Status: $($wdmMonitorService.Status)). Attempting to stop..."
        try {
            Stop-Service -Name "TomcatWDMMonitor" -Force
            Write-Host "Successfully stopped TomcatWDMMonitor service" -ForegroundColor Green
            $wdmMonitorServiceStopped = $true
        } catch {
            Write-Host "Error stopping TomcatWDMMonitor service: $_" -ForegroundColor Yellow
            Write-Host "This may cause issues during installation..."
        }
    } else {
        Write-Host "TomcatWDMMonitor service not found (this is normal if not previously installed)"
    }
} catch {
    Write-Host "Error checking for TomcatWDMMonitor service: $_" -ForegroundColor Yellow
}

# ============================================
# Step 2: Terminate Processes on Port 8080 (Tomcat)
# ============================================
Write-Host ""
Write-Host "=== Step 2: Checking for Tomcat on port 8080 ===" -ForegroundColor Cyan
$port8080TerminationSuccess = $true

if (Test-PortInUse -Port 8080) {
    $process = Get-ProcessByPort -Port 8080
    if ($process) {
        Write-Host "Found process using port 8080: $($process.Name) (PID: $($process.Id))"

        # Check if it's a Tomcat process
        $isTomcat = $process.Name -eq "java" -or $process.Name -eq "tomcat" -or $process.Path -match "tomcat"

        if ($isTomcat) {
            Write-Host "Detected Tomcat process. Attempting to stop Tomcat service..."

            # Try to stop via service first (excluding TomcatWDMMonitor which we already handled)
            $tomcatServices = Get-Service | Where-Object {
                ($_.DisplayName -like "*Tomcat*" -or $_.Name -like "*Tomcat*") -and
                $_.Name -ne "TomcatWDMMonitor"
            }
            $serviceFound = $false

            if ($tomcatServices.Count -gt 0) {
                Write-Host "Found $($tomcatServices.Count) Tomcat service(s) (excluding TomcatWDMMonitor)"
                foreach ($service in $tomcatServices) {
                    Write-Host "Stopping service: $($service.DisplayName) ($($service.Name))"
                    try {
                        Stop-Service -Name $service.Name -Force
                        $serviceFound = $true
                        Write-Host "Successfully stopped service: $($service.Name)" -ForegroundColor Green
                    } catch {
                        Write-Host "Error stopping service $($service.Name): $_" -ForegroundColor Yellow
                    }
                }
            }

            # If no service found or service stop failed, try to kill the process
            if (-not $serviceFound -or (Test-PortInUse -Port 8080)) {
                Write-Host "Attempting to terminate process directly..."
                try {
                    Stop-Process -Id $process.Id -Force
                    Write-Host "Process terminated successfully" -ForegroundColor Green
                    $port8080TerminationSuccess = $true
                } catch {
                    Write-Host "Error terminating process: $_" -ForegroundColor Red
                    $port8080TerminationSuccess = $false
                }
            } else {
                $port8080TerminationSuccess = $true
            }
        } else {
            Write-Host "Non-Tomcat process detected on port 8080. Attempting to terminate..."
            try {
                Stop-Process -Id $process.Id -Force
                Write-Host "Process terminated successfully" -ForegroundColor Green
                $port8080TerminationSuccess = $true
            } catch {
                Write-Host "Error terminating process: $_" -ForegroundColor Red
                $port8080TerminationSuccess = $false
            }
        }
    } else {
        Write-Host "Port 8080 is in use but could not identify the process. Continuing..."
        $port8080TerminationSuccess = $true
    }
} else {
    Write-Host "No process found using port 8080" -ForegroundColor Green
    $port8080TerminationSuccess = $true
}

# ============================================
# Step 3: Terminate Processes on Port 4333 (Application)
# ============================================
Write-Host ""
Write-Host "=== Step 3: Checking for services on port 4333 ===" -ForegroundColor Cyan
$port4333TerminationSuccess = $true

if (Test-PortInUse -Port 4333) {
    $process = Get-ProcessByPort -Port 4333
    if ($process) {
        Write-Host "Found process using port 4333: $($process.Name) (PID: $($process.Id))"
        Write-Host "Attempting to terminate process..."
        try {
            Stop-Process -Id $process.Id -Force
            Write-Host "Process terminated successfully" -ForegroundColor Green
            $port4333TerminationSuccess = $true
        } catch {
            Write-Host "Error terminating process: $_" -ForegroundColor Red
            $port4333TerminationSuccess = $false
        }
    }
} else {
    Write-Host "No process found using port 4333" -ForegroundColor Green
    $port4333TerminationSuccess = $true
}

# Check if process termination failed
if (-not $port8080TerminationSuccess -or -not $port4333TerminationSuccess) {
    Write-Host ""
    Write-Host "Error: Process termination failed. Installation cannot continue." -ForegroundColor Red

    if (-not $port8080TerminationSuccess) {
        Write-Host "Failed to terminate process on port 8080" -ForegroundColor Red
    }
    if (-not $port4333TerminationSuccess) {
        Write-Host "Failed to terminate process on port 4333" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "Press any key to exit..." -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# ============================================
# Step 4: Wait for TCP Connections to Clear
# ============================================
Write-Host ""
Write-Host "=== Step 4: Waiting for TCP connections to clear ===" -ForegroundColor Cyan
Write-Host "All processes successfully terminated. Waiting for TCP states to clear..." -ForegroundColor Green

$maxWaitTime = 120  # Maximum wait time in seconds (2 minutes)
$checkInterval = 5  # Check every 5 seconds
$elapsedTime = 0

Write-Host "Checking for lingering TCP connections on ports 8080 and 4333..."

while ($elapsedTime -lt $maxWaitTime) {
    # Check for any TCP connections in transitional states on our ports
    $tcpConnections = netstat -an | Select-String ":8080|:4333" | Select-String "CLOSE_WAIT|TIME_WAIT|FIN_WAIT_1|FIN_WAIT_2|CLOSING|LAST_ACK"

    if ($tcpConnections.Count -eq 0) {
        Write-Host "No lingering TCP connections found. Ports are clean." -ForegroundColor Green
        break
    } else {
        Write-Host "Found $($tcpConnections.Count) lingering TCP connection(s). Waiting for them to expire..."
        $tcpConnections | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
        Start-Sleep -Seconds $checkInterval
        $elapsedTime += $checkInterval
    }
}

if ($elapsedTime -ge $maxWaitTime) {
    Write-Host "Warning: Some TCP connections may still be lingering after $maxWaitTime seconds, but proceeding anyway." -ForegroundColor Yellow
}

# Additional short wait to ensure everything is settled
Write-Host "Waiting additional 5 seconds for final cleanup..."
Start-Sleep -Seconds 5

# ============================================
# Step 5: Backup Existing WDM Installation
# ============================================
Write-Host ""
Write-Host "=== Step 5: Backup existing WDM installation ===" -ForegroundColor Cyan

if (Test-Path $install_dir) {
    Write-Host "Creating backup of existing WDM installation..."
    # Create a timestamp for the backup folder
    $backupTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDir = "$install_dir.backup_$backupTimestamp"

    # Remove old backup if it exists
    if (Test-Path $backupDir) {
        Write-Host "Removing old backup directory..."
        try {
            Remove-Item -Path $backupDir -Recurse -Force
            Write-Host "Old backup directory removed successfully"
        } catch {
            Write-Host "Error removing old backup directory: $_" -ForegroundColor Yellow
            Write-Host "Continuing with installation..."
        }
    }

    # Create backup
    try {
        Write-Host "Copying WDM directory to backup location..."
        Copy-Item -Path $install_dir -Destination $backupDir -Recurse -Force

        # Verify backup was successful
        if (Test-Path $backupDir) {
            Write-Host "Backup completed successfully to: $backupDir" -ForegroundColor Green

            # Wait an additional 5 seconds to ensure backup is fully complete
            Write-Host "Waiting 5 seconds for backup file operations to complete..."
            Start-Sleep -Seconds 5

            # Clean the WDM directory
            Write-Host "Cleaning existing WDM directory..."
            try {
                Get-ChildItem -Path $install_dir -Recurse | Remove-Item -Force -Recurse
                Write-Host "WDM directory cleaned successfully" -ForegroundColor Green
            } catch {
                Write-Host "Error cleaning WDM directory: $_" -ForegroundColor Yellow
                Write-Host "Continuing with installation..."
            }
        } else {
            Write-Host "Error: Backup directory was not created" -ForegroundColor Red
        }
    } catch {
        Write-Host "Error creating backup: $_" -ForegroundColor Red
        Write-Host "Do you want to continue with the installation without a backup? (Y/N)" -ForegroundColor Yellow
        $response = Read-Host
        if ($response -ne "Y" -and $response -ne "y") {
            Write-Host "Installation aborted by user."
            Write-Host ""
            Write-Host "Press any key to exit..." -ForegroundColor Cyan
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            exit 1
        }
    }
} else {
    Write-Host "No existing WDM installation found. Skipping backup."
}

Write-Host ""
Write-Host "================================================================="
Write-Host "             WDM PRE-INSTALLATION TASKS COMPLETED                " -ForegroundColor Green
Write-Host "================================================================="
Write-Host ""

# ============================================
# Step 6: Run WDM Installation as Normal User
# ============================================
Write-Host "=== Step 6: Running WDM Installation (as normal user) ===" -ForegroundColor Cyan
Write-Host "Installing WDM component with:"
Write-Host "- Workstation ID: 200"
Write-Host "- Offline Mode: Disabled"
if ($VersionOverride) {
    Write-Host "- Version Override: $VersionOverride"
}
if ($SkipStoreInit) {
    Write-Host "- Skip Store Init: Enabled"
}
Write-Host ""

# Get the current user (before elevation)
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

# Create a scheduled task to run the installation as the current user (non-elevated)
$taskName = "CoopWDMInstall_" + (Get-Date -Format "yyyyMMddHHmmss")
$scriptPath = Join-Path $PSScriptRoot "GKInstall.ps1"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -ComponentType WDM -workstationId 200 -Env Dev"
if ($VersionOverride) {
    $escapedOverride = $VersionOverride.Replace('"', '""')
    $arguments += " -VersionOverride `"$escapedOverride`""
}
if ($SkipStoreInit) {
    $arguments += " -SkipStoreInit"
}

Write-Host "Creating temporary scheduled task: $taskName" -ForegroundColor Gray

try {
    # Create the scheduled task action
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory $PSScriptRoot

    # Create the task principal (run as current user, non-elevated)
    $principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited

    # Create the task settings
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)

    # Register the task
    Register-ScheduledTask -TaskName $taskName -Action $action -Principal $principal -Settings $settings -Force | Out-Null

    Write-Host "Starting installation..." -ForegroundColor Green
    Write-Host ""

    # Start the task
    Start-ScheduledTask -TaskName $taskName

    # Wait for the task to complete
    $timeout = 0
    $maxTimeout = 7200  # 2 hours in seconds

    while ($timeout -lt $maxTimeout) {
        $task = Get-ScheduledTask -TaskName $taskName
        $taskInfo = Get-ScheduledTaskInfo -TaskName $taskName

        if ($task.State -eq "Ready" -and $taskInfo.LastRunTime -gt (Get-Date).AddMinutes(-5)) {
            # Task has completed
            Write-Host ""
            if ($taskInfo.LastTaskResult -eq 0) {
                Write-Host "Installation completed successfully!" -ForegroundColor Green
            } else {
                Write-Host "Installation completed with exit code: $($taskInfo.LastTaskResult)" -ForegroundColor Yellow
            }
            break
        }

        Start-Sleep -Seconds 2
        $timeout += 2
    }

    if ($timeout -ge $maxTimeout) {
        Write-Host "Installation timed out after 2 hours" -ForegroundColor Red
    }

} catch {
    Write-Host "Error running installation: $_" -ForegroundColor Red
} finally {
    # Clean up the scheduled task
    Write-Host "Cleaning up scheduled task..." -ForegroundColor Gray
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
}

Write-Host ""

# ============================================
# Step 7: Restart TomcatWDMMonitor Service
# ============================================
Write-Host "=== Step 7: Restarting TomcatWDMMonitor Service ===" -ForegroundColor Cyan

$wdmMonitorService = Get-Service -Name "TomcatWDMMonitor" -ErrorAction SilentlyContinue
if ($wdmMonitorService) {
    Write-Host "Starting TomcatWDMMonitor service..."
    Start-Service -Name "TomcatWDMMonitor" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    # Verify service started
    $wdmMonitorService = Get-Service -Name "TomcatWDMMonitor" -ErrorAction SilentlyContinue
    if ($wdmMonitorService.Status -eq "Running") {
        Write-Host "TomcatWDMMonitor service is now running" -ForegroundColor Green
    } else {
        Write-Host "Warning: TomcatWDMMonitor service failed to start (Status: $($wdmMonitorService.Status))" -ForegroundColor Yellow
    }
} else {
    Write-Host "TomcatWDMMonitor service not found (skip restart)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "WDM Installation Complete" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
