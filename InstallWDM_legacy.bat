@echo off
:: Coop Sweden WDM Installation Wrapper
:: This batch file simply calls the PowerShell wrapper which handles:
:: - Service management (TomcatWDMMonitor stop/start)
:: - Running installation as normal user
:: - Admin elevation when needed
::
:: Any arguments passed to this batch file are forwarded to the PS1 wrapper.
:: Examples:
::   InstallWDM_legacy.bat -VersionOverride v5.27.1
::   InstallWDM_legacy.bat -SkipStoreInit
::   InstallWDM_legacy.bat -VersionOverride v5.27.1 -SkipStoreInit

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0InstallWDM_legacy.ps1" %*
