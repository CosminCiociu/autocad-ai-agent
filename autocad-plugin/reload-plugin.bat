@echo off
REM Quick reload script for AutoCAD plugin
REM Run this batch file to reload the plugin after building

setlocal enabledelayedexpansion

set "DLL_PATH=E:\AiAgentBuild\AutocadPlugin.dll"
set "OLD_DLL=e:\Ai agent\autocad-plugin\bin\Debug\net48\AutocadPlugin.dll"

echo Attempting to reload AutoCAD plugin...
echo DLL: %DLL_PATH%
echo.

REM Try to reload using PowerShell script
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0reload-plugin.ps1" -DllPath "%DLL_PATH%"

if errorlevel 1 (
    echo.
    echo MANUAL RELOAD STEPS:
    echo 1. In AutoCAD, type: UNLOAD
    echo 2. Select: %OLD_DLL%
    echo 3. In AutoCAD, type: NETLOAD
    echo 4. Select: %DLL_PATH%
    echo.
    pause
) else (
    echo.
    echo Plugin reload initiated successfully!
    echo Wait a few seconds in AutoCAD for the reload to complete.
)

endlocal
