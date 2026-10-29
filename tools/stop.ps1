$ErrorActionPreference = 'SilentlyContinue'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$appPath = Join-Path $root 'src\app.py'
$matches = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -in @('python.exe','pythonw.exe') -and $_.CommandLine -and
    $_.CommandLine.IndexOf($appPath, [StringComparison]::OrdinalIgnoreCase) -ge 0
}
if (-not $matches) { Write-Output 'TSPL Label Desk process not found.'; exit 0 }
foreach ($process in $matches) { Stop-Process -Id $process.ProcessId -Force }
Write-Output ("Stopped {0} TSPL Label Desk process(es)." -f @($matches).Count)
