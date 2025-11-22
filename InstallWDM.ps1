<#
.SYNOPSIS
    Coop Sweden WDM Installation Wrapper with Service Management
.DESCRIPTION
    All-in-one wrapper that:
    1. Requests administrator privileges for service management
    2. Stops TomcatWDMMonitor service
    3. Runs GKInstall.ps1 as normal user (non-elevated)
    4. Waits for installation to complete
    5. Restarts TomcatWDMMonitor service

    This ensures the installation runs without admin privileges while
    still managing the Windows service that requires elevation.
#>

# Self-elevate the script if required
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Requesting administrator privileges..." -ForegroundColor Yellow
    Write-Host "Please click 'Yes' in the UAC prompt to continue." -ForegroundColor Yellow
    Start-Sleep -Seconds 2

    # Relaunch as administrator with explicit directory change
    $scriptPath = $PSCommandPath
    $scriptDir = $PSScriptRoot
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -Command `"Set-Location '$scriptDir'; & '$scriptPath'`"" -Verb RunAs
    exit
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Coop Sweden WDM Installation" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Running with administrator privileges for service management" -ForegroundColor Green
Write-Host ""

# ============================================
# Step 1: Stop TomcatWDMMonitor Service
# ============================================
Write-Host "=== Step 1: Stopping TomcatWDMMonitor Service ===" -ForegroundColor Cyan
$wdmMonitorService = Get-Service -Name "TomcatWDMMonitor" -ErrorAction SilentlyContinue

if ($wdmMonitorService) {
    Write-Host "Found TomcatWDMMonitor service (Status: $($wdmMonitorService.Status))"
    if ($wdmMonitorService.Status -eq "Running") {
        Write-Host "Stopping TomcatWDMMonitor service..." -ForegroundColor Yellow
        Stop-Service -Name "TomcatWDMMonitor" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2

        $wdmMonitorService = Get-Service -Name "TomcatWDMMonitor" -ErrorAction SilentlyContinue
        if ($wdmMonitorService.Status -eq "Stopped") {
            Write-Host "TomcatWDMMonitor service stopped successfully" -ForegroundColor Green
        } else {
            Write-Host "Warning: Service may not have stopped completely (Status: $($wdmMonitorService.Status))" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Service is already stopped" -ForegroundColor Gray
    }
} else {
    Write-Host "TomcatWDMMonitor service not found (first-time install)" -ForegroundColor Gray
}

Write-Host ""

# ============================================
# Step 2: Run WDM Installation as Normal User
# ============================================
Write-Host "=== Step 2: Running WDM Installation (as normal user) ===" -ForegroundColor Cyan
Write-Host "Installing WDM component with:"
Write-Host "- Workstation ID: 200"
Write-Host "- Offline Mode: Enabled"
Write-Host ""

# Get the current user (before elevation)
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

# Create a scheduled task to run the installation as the current user (non-elevated)
$taskName = "CoopWDMInstall_" + (Get-Date -Format "yyyyMMddHHmmss")
$scriptPath = Join-Path $PSScriptRoot "GKInstall.ps1"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -ComponentType WDM -workstationId 200 -offline"

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
# Step 3: Restart TomcatWDMMonitor Service
# ============================================
Write-Host "=== Step 3: Restarting TomcatWDMMonitor Service ===" -ForegroundColor Cyan

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
