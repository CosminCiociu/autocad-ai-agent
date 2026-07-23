# Script to automatically reload AutocadPlugin.dll in running AutoCAD instance

param(
    [string]$DllPath = "E:\AiAgentBuild\AutocadPlugin.dll"
)

try {
    # Get running AutoCAD instance
    $acad = [System.Runtime.InteropServices.Marshal]::GetActiveObject("AutoCAD.Application")
    
    if ($null -eq $acad) {
        Write-Host "ERROR: No running AutoCAD instance found"
        exit 1
    }
    
    Write-Host "Found running AutoCAD instance"
    
    # Get the active document
    $doc = $acad.ActiveDocument
    
    if ($null -eq $doc) {
        Write-Host "ERROR: No active document in AutoCAD"
        exit 1
    }
    
    # Send the reload commands to the document
    Write-Host "Sending reload command to AutoCAD..."
    
    # Unload old DLL and load new one
    $doc.SendCommand("(command `"UNLOAD`" `"e:\\Ai agent\\autocad-plugin\\bin\\Debug\\net48\\AutocadPlugin.dll`")`n")
    Start-Sleep -Milliseconds 500
    $doc.SendCommand("(command `"NETLOAD`" `"$DllPath`")`n")
    
    Write-Host "SUCCESS: Plugin reload command sent to AutoCAD"
    exit 0
}
catch {
    Write-Host "ERROR: $_"
    
    # Fallback: try using type library
    try {
        $acad = New-Object -ComObject AutoCAD.Application
        $doc = $acad.ActiveDocument
        
        Write-Host "Found AutoCAD via COM, sending reload command..."
        
        $doc.SendCommand("(command `"UNLOAD`" `"e:\\Ai agent\\autocad-plugin\\bin\\Debug\\net48\\AutocadPlugin.dll`")`n")
        Start-Sleep -Milliseconds 500
        $doc.SendCommand("(command `"NETLOAD`" `"$DllPath`")`n")
        
        Write-Host "SUCCESS: Plugin reload command sent to AutoCAD"
        exit 0
    }
    catch {
        Write-Host "ERROR: Could not communicate with AutoCAD: $_"
        Write-Host ""
        Write-Host "MANUAL WORKAROUND:"
        Write-Host "1. In AutoCAD, type: UNLOAD"
        Write-Host "2. Select: e:\Ai agent\autocad-plugin\bin\Debug\net48\AutocadPlugin.dll"
        Write-Host "3. In AutoCAD, type: NETLOAD"
        Write-Host "4. Select: $DllPath"
        exit 1
    }
}
