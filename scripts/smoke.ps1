param([Parameter(Mandatory=$true)][string]$ZipPath)
$ErrorActionPreference='Stop'
# Runs only on an isolated GitHub-hosted Windows runner, using a throwaway extracted ZIP.
$smoke=Join-Path $env:RUNNER_TEMP 'freecrawl-portable-smoke'
if (Test-Path $smoke) { Remove-Item $smoke -Recurse -Force }
New-Item -ItemType Directory -Path $smoke | Out-Null
Expand-Archive -LiteralPath $ZipPath -DestinationPath $smoke
$root=Join-Path $smoke 'FreeCrawlPortable'
$launcher=Join-Path $root 'FreeCrawlPortable.exe'
function Stop-TestProcesses([string]$directory) {
    # Narrow scope: terminate only copies of FreeCrawl started from this test directory.
    $procs=Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($directory,[System.StringComparison]::OrdinalIgnoreCase) }
    foreach ($proc in $procs) {
        try { Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
    }
    Start-Sleep -Seconds 2
}
function Test-Launch([string]$directory) {
    $start=Join-Path $directory 'FreeCrawlPortable.exe'
    $started=Start-Process -FilePath $start -WorkingDirectory $directory -PassThru
    $debug=Join-Path $directory 'Data\Profile\debug.txt'
    $deadline=(Get-Date).AddSeconds(50)
    try {
        while ((Get-Date) -lt $deadline) {
            if (Test-Path $debug) {
                $size=(Get-Item $debug).Length
                if ($size -gt 0) {
                    Write-Host "PASS: live application wrote portable profile debug.txt ($size bytes)."
                    return
                }
            }
            Start-Sleep -Seconds 2
            $started.Refresh()
            if ($started.HasExited) { throw 'Portable launcher exited before the application initialized.' }
        }
        throw 'The application did not produce its expected portable-profile debug.txt within 50 seconds.'
    } finally { Stop-TestProcesses $directory }
}
try {
    Test-Launch $root
    $sentinel=Join-Path $root 'Data\Profile\relocation-test.txt'
    Set-Content -LiteralPath $sentinel -Value 'Keep me after folder moves' -Encoding UTF8
    $moved=Join-Path $smoke 'RelocatedFreeCrawlPortable'
    Move-Item -LiteralPath $root -Destination $moved
    if (-not (Test-Path (Join-Path $moved 'Data\Profile\relocation-test.txt'))) {
        throw 'Existing portable profile disappeared on relocation.'
    }
    Test-Launch $moved
    if (-not (Test-Path (Join-Path $moved 'Data\Profile\relocation-test.txt'))) {
        throw 'Existing profile was overwritten after relocation.'
    }
    Write-Host 'PASS: Windows launch, userData redirection, folder move, persistent Data retention.'
} finally {
    Stop-TestProcesses $root
    if ($moved) { Stop-TestProcesses $moved }
}
