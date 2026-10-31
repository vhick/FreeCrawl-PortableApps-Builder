# Verify the built .paf.exe by genuinely installing and upgrading a disposable test copy.
param([Parameter(Mandatory=$true)][string]$Installer, [Parameter(Mandatory=$true)][string]$Version)
$ErrorActionPreference = 'Stop'
$installerPath = (Resolve-Path -LiteralPath $Installer).Path
$testRoot = Join-Path $env:RUNNER_TEMP 'freecrawl-paf-install-qa'
if (Test-Path $testRoot) { Remove-Item -LiteralPath $testRoot -Force -Recurse }
New-Item -ItemType Directory -Path $testRoot | Out-Null
if ($testRoot.Contains(' ')) { throw 'NSIS /D= test destination must not include spaces' }
function Run-PafInstall([string]$target) {
    $info = [System.Diagnostics.ProcessStartInfo]::new($installerPath)
    $info.UseShellExecute = $false
    [void]$info.ArgumentList.Add('/S')
    [void]$info.ArgumentList.Add("/D=$target")
    $process = [System.Diagnostics.Process]::Start($info)
    if (-not $process) { throw 'Cannot start official PAF installer' }
    if (-not $process.WaitForExit(300000)) { $process.Kill(); throw 'PAF installation timed out' }
    if ($process.ExitCode -ne 0) { throw "PAF installer exited $($process.ExitCode)" }
}
function Check-Installed() {
    $root = Join-Path $testRoot 'FreeCrawlPortable'
    $exe = Join-Path $root 'FreeCrawlPortable.exe'
    $app = Join-Path $root 'App\FreeCrawl\FreeCrawl SEO Tool.exe'
    $meta = Join-Path $root 'App\AppInfo\appinfo.ini'
    foreach ($file in @($exe, $app, $meta)) {
        if (-not (Test-Path -LiteralPath $file)) { throw "PAF installer did not install required file: $file" }
    }
    if (-not (Select-String -LiteralPath $meta -SimpleMatch 'Start=FreeCrawlPortable.exe' -Quiet)) {
        throw 'Installed appinfo.ini does not reference the native EXE launcher'
    }
    return $root
}
Write-Host 'TEST: clean install of genuine PAF into disposable folder'
Run-PafInstall $testRoot
$root = Check-Installed
$dataPath = Join-Path $root 'Data'
New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
$sentinel = Join-Path $dataPath 'keep-existing-data.txt'
Set-Content -LiteralPath $sentinel -Value 'Never delete user profiles on upgrade' -Encoding utf8
Write-Host 'TEST: upgrade by running the same official installer a second time'
Run-PafInstall $testRoot
[void](Check-Installed)
if (-not (Test-Path -LiteralPath $sentinel)) { throw 'Existing Data was destroyed by installer upgrade!' }
if ((Get-Content -LiteralPath $sentinel -Raw) -notmatch 'Never delete') { throw 'Existing Data contents changed on upgrade' }
Write-Host "PASS: official PAF clean install, native EXE, metadata, and Data preservation after upgrade ($Version)."
