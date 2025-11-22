@echo off
:: Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    echo Please click 'Yes' in the UAC prompt to continue.
    timeout /t 2 /nobreak >nul
    :: Relaunch with admin elevation
    powershell.exe -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ============================================
echo Coop Sweden WDM Installation
echo ============================================
echo.
echo Running with administrator privileges
echo.
echo Installing WDM component with:
echo - Workstation ID: 200
echo - Offline Mode: Enabled
echo.
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0GKInstall.ps1" -ComponentType WDM -workstationId 200 -offline
echo.
pause
