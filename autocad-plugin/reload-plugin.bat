@echo off
REM One-command build and reload script for AutoCAD plugin

setlocal enabledelayedexpansion

set "PROJECT_PATH=E:\Ai agent\autocad-plugin\AutocadPlugin.csproj"
set "OUTPUT_DIR=E:\Ai agent\autocad-plugin\bin\Debug\net48"
set "DLL_PATH=E:\Ai agent\autocad-plugin\bin\Debug\net48\AutocadPlugin.dll"

echo Building and reloading AutoCAD plugin...
echo DLL: %DLL_PATH%
echo.

REM Build and reload using PowerShell script
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0reload-plugin.ps1" -ProjectPath "%PROJECT_PATH%" -OutputDir "%OUTPUT_DIR%" -DllPath "%DLL_PATH%"

if errorlevel 1 (
    echo.
    echo Build or reload failed.
    echo If build succeeded and AutoCAD is open, run in AutoCAD:
    echo 1. NETLOAD
    echo 2. %DLL_PATH%
    echo.
    pause
) else (
    echo.
    echo Plugin build + reload initiated successfully.
)

endlocal
