# FreeCrawl PortableApps installer build: use the UNMODIFIED official PortableApps.com Installer.
# Prior r4 failure: launching the Installer TOOL's .paf.exe installer and waiting for its
# setup wizard blocked a headless GitHub Actions runner for 97+ minutes.
# We now EXTRACT that SHA-256-verified vendor distribution with 7-Zip (no setup wizard)
# and run its original PortableApps.comInstaller.exe using its documented app-folder argument.
param(
    [Parameter(Mandatory=$true)][string]$Version,
    [Parameter(Mandatory=$true)][string]$Revision
)
$ErrorActionPreference = 'Stop'
$toolVersion = '3.9.22'
$expectedSha256 = '689456f1fb1320c45e82a077afe6b87fb388fd3f75c41d9ee9ce8d45f3966b67'
$toolName = "PortableApps.comInstaller_$toolVersion.paf.exe"
if (-not $env:RUNNER_TEMP) { throw 'RUNNER_TEMP must be set on the GitHub Actions runner.' }
$toolHome = Join-Path $env:RUNNER_TEMP 'freecrawl-official-installer'
$toolDownload = Join-Path $toolHome $toolName
$toolExtract = Join-Path $toolHome 'extracted'
$stageParent = (Resolve-Path 'stage').Path
$stage = Join-Path $stageParent 'FreeCrawlPortable'
$dist = Join-Path (Get-Location).Path 'dist'
if (-not (Test-Path -LiteralPath (Join-Path $stage 'App\AppInfo\appinfo.ini') -PathType Leaf)) {
    throw 'PortableApps staging folder is missing its appinfo.ini'
}
if (-not (Test-Path -LiteralPath $toolDownload -PathType Leaf)) {
    throw "Verified installer distribution missing: $toolDownload. Check scripts/acquire_installer.ps1."
}
$toolHash = (Get-FileHash -LiteralPath $toolDownload -Algorithm SHA256).Hash.ToLowerInvariant()
if ($toolHash -ne $expectedSha256) { throw "Installer SHA-256 mismatch: $toolHash" }
$toolFile = [System.IO.File]::OpenRead($toolDownload)
try {
    if ($toolFile.Length -lt 100000 -or $toolFile.ReadByte() -ne 0x4d -or $toolFile.ReadByte() -ne 0x5a) {
        throw 'Official vendor installer distribution is not a valid-sized Windows executable.'
    }
} finally { $toolFile.Dispose() }
Write-Host "Verified official PortableApps.com Installer $toolVersion (SHA-256 $toolHash)."

# Explicit timeout for EVERY third-party executable in this build phase.
# .NET ArgumentList avoids quoting issues for executable paths containing spaces.
function Invoke-BoundedProgram {
    param(
        [Parameter(Mandatory=$true)][string]$Exe,
        [Parameter(Mandatory=$true)][string[]]$Arguments,
        [Parameter(Mandatory=$true)][string]$WorkingDir,
        [Parameter(Mandatory=$true)][int]$TimeoutSeconds,
        [Parameter(Mandatory=$true)][string]$Label
    )
    $info = [System.Diagnostics.ProcessStartInfo]::new($Exe)
    $info.UseShellExecute = $false
    $info.WorkingDirectory = $WorkingDir
    foreach ($arg in $Arguments) { [void]$info.ArgumentList.Add($arg) }
    $proc = [System.Diagnostics.Process]::Start($info)
    if (-not $proc) { throw "Cannot start $Label ($Exe)" }
    try {
        if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
            try { $proc.Kill($true) } catch { try { $proc.Kill() } catch {} }
            throw "$Label exceeded its $TimeoutSeconds-second limit (no unattended GUI waits allowed)."
        }
        if ($proc.ExitCode -ne 0) { throw "$Label failed with exit code $($proc.ExitCode)." }
    } finally { $proc.Dispose() }
}

# Do not EXECUTE the downloaded .paf.exe. It is itself a GUI installer, not the
# command-line packager. Extracting the verified NSIS archive is deterministic.
$sevenZipCandidates = @(
    'C:\Program Files\7-Zip\7z.exe',
    'C:\Program Files (x86)\7-Zip\7z.exe'
)
$sevenZip = $null
foreach ($candidate in $sevenZipCandidates) {
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $sevenZip = $candidate; break }
}
if (-not $sevenZip) {
    $cmd = Get-Command '7z.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) { $sevenZip = $cmd.Source }
}
if (-not $sevenZip) { throw '7-Zip 7z.exe is unavailable on the Windows runner.' }
if (Test-Path -LiteralPath $toolExtract) { Remove-Item -LiteralPath $toolExtract -Recurse -Force }
New-Item -ItemType Directory -Path $toolExtract, $dist -Force | Out-Null
Write-Host "Extracting verified vendor package with: $sevenZip"
Invoke-BoundedProgram -Exe $sevenZip -Arguments @('x', $toolDownload, "-o$toolExtract", '-y', '-bd') `
    -WorkingDir $toolHome -TimeoutSeconds 120 -Label 'Official tool archive extraction'

# PortableApps packages normally store a complete App/PortableApps.comInstaller
# directory. Find the tool rather than guessing the exact NSIS extraction prefix.
$candidates = @(Get-ChildItem -LiteralPath $toolExtract -Recurse -File -Filter 'PortableApps.comInstaller.exe')
if ($candidates.Count -ne 1) {
    $files = @(Get-ChildItem -LiteralPath $toolExtract -Recurse -File | Select-Object -First 40 -ExpandProperty FullName)
    throw "Expected exactly one PortableApps.comInstaller.exe in the verified vendor archive; found $($candidates.Count). Extracted sample: $($files -join '; ')"
}
$builderExe = $candidates[0].FullName
if ((Get-Item $builderExe).Length -lt 10000) { throw 'Extracted vendor builder executable is unexpectedly small.' }
$stream = [System.IO.File]::OpenRead($builderExe)
try {
    if ($stream.ReadByte() -ne 0x4d -or $stream.ReadByte() -ne 0x5a) {
        throw 'Extracted official builder lacks the Windows MZ header.'
    }
} finally { $stream.Dispose() }
Write-Host "Extracted original PortableApps.comInstaller.exe: $builderExe"
Write-Host 'Building FreeCrawl .paf.exe with the original unmodified PortableApps.com Installer tool.'

# The official tool documents accepting a portable application's root folder on
# its command line. It must finish without user input. Fail in 8 minutes, not 100.
Invoke-BoundedProgram -Exe $builderExe -Arguments @($stage) `
    -WorkingDir (Split-Path -Parent $builderExe) -TimeoutSeconds 480 `
    -Label 'Official PortableApps installer compilation'

$generated = @(Get-ChildItem -LiteralPath $stageParent -File -Filter 'FreeCrawlPortable_*.paf.exe')
if ($generated.Count -ne 1) {
    $logs = @(Get-ChildItem -LiteralPath (Join-Path $stage 'App\AppInfo') -File -Filter '*installer*log*')
    foreach ($log in $logs) { Write-Host "Installer log: $($log.FullName)"; Get-Content -LiteralPath $log.FullName -Tail 75 }
    throw "Official installer exited without exactly one expected FreeCrawlPortable_*.paf.exe in $stageParent. Found $($generated.Count)."
}
$target = Join-Path $dist "FreeCrawlPortable_v${Version}_r${Revision}_win64.paf.exe"
if (Test-Path -LiteralPath $target) { throw "Refusing to overwrite existing PAF: $target" }
Move-Item -LiteralPath $generated[0].FullName -Destination $target
# Verify both the MZ/PE signature and installed payload in the follow-up workflow.
$bytes = [System.IO.File]::ReadAllBytes($target)
if ($bytes.Length -lt 100000 -or $bytes[0] -ne 0x4d -or $bytes[1] -ne 0x5a) {
    throw 'Official .paf.exe output has no executable header or is too small.'
}
$offset = [BitConverter]::ToInt32($bytes, 0x3c)
if ($offset -lt 0x40 -or $offset -gt $bytes.Length - 6 -or
    $bytes[$offset] -ne 0x50 -or $bytes[$offset + 1] -ne 0x45) {
    throw 'Official .paf.exe output has no valid Windows PE signature.'
}
Write-Host "PASS: Original PortableApps.com Installer produced $target ($($bytes.Length) bytes)."
