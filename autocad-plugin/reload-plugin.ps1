# Build and reload AutocadPlugin.dll into a running AutoCAD instance.

param(
    [string]$ProjectPath = "E:\Ai agent\autocad-plugin\AutocadPlugin.csproj",
    [string]$OutputDir = ".\bin\Debug\net48",
    [string]$DllPath = "",
    [switch]$SkipBuild,
    [switch]$UseVersionedDll = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AcadDocument {
    try {
        $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
        if ($null -eq $acad) {
            return $null
        }
        return $acad.ActiveDocument
    }
    catch {
        return $null
    }
}

function Send-ReloadCommands {
    param(
        [Parameter(Mandatory = $true)]
        $Document,
        [Parameter(Mandatory = $true)]
        [string]$PluginPath
    )

    # Use forward slashes to avoid escaping issues in command strings.
    $normalizedPath = $PluginPath -replace "\\", "/"

    # Ensure AutoCAD is in a clean command state.
    $Document.SendCommand("`x`x")
    Start-Sleep -Milliseconds 250

    # NETUNLOAD is optional (depends on AutoCAD version/state).
    $Document.SendCommand("_.NETUNLOAD `"$normalizedPath`" `n")
    Start-Sleep -Milliseconds 400

    $Document.SendCommand("_.NETLOAD `"$normalizedPath`" `n")
}

function Invoke-WithRetry {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Action,
        [int]$MaxAttempts = 8,
        [int]$DelayMs = 400
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            & $Action
            return
        }
        catch [System.Runtime.InteropServices.COMException] {
            $hresult = $_.Exception.HResult
            # RPC_E_CALL_REJECTED (-2147418111): AutoCAD is temporarily busy.
            if ($hresult -eq -2147418111 -and $attempt -lt $MaxAttempts) {
                Start-Sleep -Milliseconds $DelayMs
                continue
            }
            throw
        }
    }
}

function New-VersionedDllCopy {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceDllPath
    )

    $dir = Split-Path -Parent $SourceDllPath
    $base = [System.IO.Path]::GetFileNameWithoutExtension($SourceDllPath)
    $ext = [System.IO.Path]::GetExtension($SourceDllPath)
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss_fff"
    $target = Join-Path $dir ("{0}_{1}{2}" -f $base, $stamp, $ext)

    Copy-Item -LiteralPath $SourceDllPath -Destination $target -Force
    return $target
}

if (-not $SkipBuild) {
    if (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
        $OutputDir = Join-Path $PSScriptRoot $OutputDir
    }

    Write-Host "Building plugin..."
    & dotnet build "$ProjectPath" -p:OutputPath="$OutputDir\\" -p:AppendTargetFrameworkToOutputPath=false -p:SkipPostBuildReload=true
    if ($LASTEXITCODE -ne 0) {
        throw "dotnet build failed with exit code $LASTEXITCODE"
    }
}

if ([string]::IsNullOrWhiteSpace($DllPath)) {
    $DllPath = Join-Path $OutputDir "AutocadPlugin.dll"
}

if (-not [System.IO.Path]::IsPathRooted($DllPath)) {
    $DllPath = Join-Path $PSScriptRoot $DllPath
}

if (-not (Test-Path -LiteralPath $DllPath)) {
    throw "Built DLL not found: $DllPath"
}

$loadPath = $DllPath
if ($UseVersionedDll) {
    $loadPath = New-VersionedDllCopy -SourceDllPath $DllPath
    Write-Host "Using versioned DLL for NETLOAD: $loadPath"
}

$doc = Get-AcadDocument
if ($null -eq $doc) {
    Write-Host "Build done, but AutoCAD is not running or has no active drawing."
    Write-Host "Manual load in AutoCAD:"
    Write-Host "  NETLOAD"
    Write-Host "  $loadPath"
    exit 0
}

Write-Host "Sending NETLOAD sequence to AutoCAD..."
Invoke-WithRetry -Action {
    Send-ReloadCommands -Document $doc -PluginPath $loadPath
}
Write-Host "SUCCESS: build + reload command sent to AutoCAD."
exit 0
