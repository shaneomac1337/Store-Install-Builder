@echo off
:: Coop Sweden WDM Installation Wrapper
:: This batch file simply calls the PowerShell wrapper which handles:
:: - Service management (TomcatWDMMonitor stop/start)
:: - Running installation as normal user
:: - Admin elevation when needed

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0InstallWDM.ps1"
