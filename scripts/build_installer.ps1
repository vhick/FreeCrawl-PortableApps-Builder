# FreeCrawl PAF build: prefer the UNMODIFIED official PortableApps.com Installer.
# If no valid official output is found, generate an explicitly independent NSIS installer.
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
# The official tool determines its generated filename from appinfo.ini. Earlier
# revisions ONLY searched for FreeCrawlPortable_*.paf.exe in stage/, wrongly
# assuming both filename AND output location, with no diagnostic inventory.
$startTime = (Get-Date).ToUniversalTime().ToString('o')
$officialStatus='official'
try {
    Invoke-BoundedProgram -Exe $builderExe -Arguments @($stage) `
        -WorkingDir (Split-Path -Parent $builderExe) -TimeoutSeconds 480 `
        -Label 'Official PortableApps installer compilation'
} catch {
    Write-Warning "Official packager did not finish successfully: $_"
    $officialStatus='fallback'
}
$target = Join-Path $dist "FreeCrawlPortable_v${Version}_r${Revision}_win64.paf.exe"
# Avoid a false failure when the official builder uses a name derived from [Details] Name.
$searchRoots=@($stageParent,(Get-Location).Path,(Split-Path -Parent (Get-Location).Path),$dist,(Split-Path -Parent $builderExe))
$locateArgs=@('scripts/locate_official_paf.py','--started',$startTime,'--sevenzip',$sevenZip,'--target',$target)
foreach ($root in $searchRoots) { $locateArgs+=@('--root',$root) }
& python @locateArgs
$locateExit=$LASTEXITCODE
if ($locateExit -ne 0 -and $locateExit -ne 2) { throw "Official PAF discovery failed with exit code $locateExit. Refusing an ambiguous package." }
if ($locateExit -eq 0) { $officialStatus='official' }
if ($locateExit -eq 2) {
    $officialStatus='fallback'
    Write-Warning 'Official installer did not create a verified package in the expected locations; using a fully disclosed independent NSIS fallback.'
    $logDirs=@((Join-Path $stage 'App\AppInfo'),(Split-Path -Parent $builderExe))
    foreach ($folder in $logDirs) {
        if (-not (Test-Path -LiteralPath $folder -PathType Container)) { continue }
        foreach ($log in @(Get-ChildItem -LiteralPath $folder -File -Filter '*installer*log*' -ErrorAction SilentlyContinue)) {
            Write-Host "Vendor builder log $($log.FullName):"
            Get-Content -LiteralPath $log.FullName -Tail 70
        }
    }
    ./scripts/build_nsis_fallback.ps1 -Version $Version -Revision $Revision
}
if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Installer package missing: $target" }
$stream=[System.IO.File]::OpenRead($target)
try {
    if ($stream.Length -lt 150000 -or $stream.ReadByte() -ne 0x4d -or $stream.ReadByte() -ne 0x5a) {
        throw 'Produced installer is not a valid-sized Windows MZ executable'
    }
    $stream.Seek(0x3c,[System.IO.SeekOrigin]::Begin) | Out-Null
    $buffer=New-Object byte[] 4
    if ($stream.Read($buffer,0,4) -ne 4) { throw 'No PE offset' }
    $offset=[BitConverter]::ToInt32($buffer,0)
    if ($offset -lt 64 -or $offset -gt 1048576) { throw 'Invalid PE offset' }
    $stream.Seek($offset,[System.IO.SeekOrigin]::Begin) | Out-Null
    if ($stream.Read($buffer,0,4) -ne 4 -or [BitConverter]::ToUInt32($buffer,0) -ne 17744) {
        throw 'Produced installer does not have a valid Windows PE header'
    }
} finally { $stream.Dispose() }
Set-Content -LiteralPath (Join-Path $dist 'installer-engine.txt') -Value $officialStatus -Encoding utf8
Write-Host "PASS: PAF file exists, matches Windows PE signature; engine=$officialStatus."
if ($officialStatus -eq 'fallback') { Write-Warning 'This .paf.exe is an independent NSIS-built installer, NOT built by the official PortableApps.com Installer.' }
