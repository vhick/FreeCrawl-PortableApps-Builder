# Build a genuine PortableApps.com installer with the UNMODIFIED official installer tool.
# All downloads are SHA-256 verified; no hidden PowerShell or execution-policy bypasses.
param(
    [Parameter(Mandatory=$true)][string]$Version,
    [Parameter(Mandatory=$true)][string]$Revision
)
$ErrorActionPreference = 'Stop'
$toolVersion = '3.9.22' # stable published 2026-10-12; review/update when official releases change
$expectedSha256 = '689456f1fb1320c45e82a077afe6b87fb388fd3f75c41d9ee9ce8d45f3966b67'
$toolName = "PortableApps.comInstaller_$toolVersion.paf.exe"
$toolHome = Join-Path $env:RUNNER_TEMP 'freecrawl-official-installer'
$toolDownload = Join-Path $toolHome $toolName
$toolInstallParent = Join-Path $toolHome 'installed'
$stageParent = (Resolve-Path 'stage').Path
$stage = Join-Path $stageParent 'FreeCrawlPortable'
$dist = Join-Path (Get-Location).Path 'dist'
if (-not (Test-Path (Join-Path $stage 'App\AppInfo\appinfo.ini'))) { throw 'PortableApps staging folder is missing' }
New-Item -ItemType Directory -Path $toolHome, $toolInstallParent, $dist -Force | Out-Null

$urls = @(
    "https://downloads.sourceforge.net/project/portableapps/PortableApps.com%20Installer/$toolName?download",
    "https://sourceforge.net/projects/portableapps/files/PortableApps.com%20Installer/$toolName/download"
)
$verified = $false
foreach ($url in $urls) {
    try {
        Write-Host "Downloading official PortableApps.com Installer $toolVersion"
        Invoke-WebRequest -Uri $url -OutFile $toolDownload -MaximumRedirection 10 -TimeoutSec 120 -ErrorAction Stop
        $actual = (Get-FileHash -LiteralPath $toolDownload -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expectedSha256) {
            Write-Warning "Downloaded file failed publisher checksum verification (SHA256=$actual)."
            Remove-Item -LiteralPath $toolDownload -Force
            continue
        }
        $verified = $true
        break
    } catch {
        Write-Warning "Official download mirror failed: $($_.Exception.Message)"
    }
}
if (-not $verified) { throw "Unable to obtain official $toolName with the verified SHA-256 hash. No installer was built." }

# Official NSIS package: silent-bootstrap the installer TOOL to a temporary directory.
# The /D= destination must be the final parameter and an unquoted directory without spaces.
if ($toolInstallParent.Contains(' ')) { throw 'Tool installation temporary path contains spaces; cannot safely use NSIS /D= argument' }
Write-Host 'Installing the verified official builder into the temporary runner directory'
$bootstrap = Start-Process -FilePath $toolDownload -ArgumentList @('/S', "/D=$toolInstallParent") -PassThru -Wait
if ($bootstrap.ExitCode -ne 0) { throw "Official installer bootstrap returned exit code $($bootstrap.ExitCode)" }
$builderCandidates = @(Get-ChildItem -LiteralPath $toolInstallParent -Recurse -File -Filter 'PortableApps.comInstaller.exe')
if ($builderCandidates.Count -ne 1) {
    throw "Expected one official PortableApps.comInstaller.exe tool but found $($builderCandidates.Count)."
}
$builderExe = $builderCandidates[0].FullName
Write-Host "Official installer build tool: $builderExe"

# Official documented command line: pass the complete portable app directory as the argument.
# Tool writes a .paf.exe in the parent of this directory.
Write-Host 'Building genuine .paf.exe using official PortableApps.com Installer'
$builderInfo = [System.Diagnostics.ProcessStartInfo]::new($builderExe)
$builderInfo.WorkingDirectory = Split-Path -Parent $builderExe
$builderInfo.UseShellExecute = $false
[void]$builderInfo.ArgumentList.Add($stage)
$builder = [System.Diagnostics.Process]::Start($builderInfo)
if (-not $builder) { throw 'Cannot start official PortableApps.com installer tool' }
if (-not $builder.WaitForExit(900000)) {
    $builder.Kill()
    throw 'Official PortableApps.com Installer timed out after 15 minutes'
}
if ($builder.ExitCode -ne 0) { throw "Official installer returned code $($builder.ExitCode)" }
$generated = @(Get-ChildItem -LiteralPath $stageParent -File -Filter 'FreeCrawlPortable_*.paf.exe')
if ($generated.Count -ne 1) {
    throw "Expected one official generated FreeCrawlPortable_*.paf.exe but found $($generated.Count). Check appinfo.ini and the official installer log."
}
$target = Join-Path $dist "FreeCrawlPortable_v${Version}_r${Revision}_win64.paf.exe"
if (Test-Path $target) { throw 'Refusing to overwrite existing PAF output: ' + $target }
Move-Item -LiteralPath $generated[0].FullName -Destination $target
$bytes = [System.IO.File]::ReadAllBytes($target)
if ($bytes.Length -lt 100000 -or $bytes[0] -ne 0x4d -or $bytes[1] -ne 0x5a) {
    throw 'Generated installer is missing an executable PE header or is too small'
}
Write-Host "Genuine official PortableApps installer produced: $target ($($bytes.Length) bytes)"
