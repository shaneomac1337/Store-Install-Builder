@echo off
echo ============================================
echo Coop Sweden WDM Installation
echo ============================================
echo.
echo Installing WDM component with:
echo - Workstation ID: 200
echo - Offline Mode: Enabled
echo.
powershell.exe -ExecutionPolicy Bypass -File "%~dp0GKInstall.ps1" -ComponentType WDM -workstationId 200 -offline
pause
