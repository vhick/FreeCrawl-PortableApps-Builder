# Acquire the official PortableApps.com Installer from official SourceForge mirror hosts.
# Run this BEFORE compilation so a mirror outage does not waste GitHub Actions minutes.
# The SHA-256 is published on the official SourceForge download page.
# Never skip checksum validation or fall back to unverified third-party downloads.
$ErrorActionPreference = 'Stop'
$toolVersion = '3.9.22'
$toolName = "PortableApps.comInstaller_$toolVersion.paf.exe"
$expectedSha256 = '689456f1fb1320c45e82a077afe6b87fb388fd3f75c41d9ee9ce8d45f3966b67'
if (-not $env:RUNNER_TEMP) { throw 'RUNNER_TEMP is required on the GitHub Actions runner.' }
$toolHome = Join-Path $env:RUNNER_TEMP 'freecrawl-official-installer'
New-Item -ItemType Directory -Path $toolHome -Force | Out-Null
$destination = Join-Path $toolHome $toolName

# Mirrors are part of the SourceForge download service, NOT unrelated hosts.
# SourceForge documents mirrors and allows the user to select another mirror
# when one is unavailable. Each candidate is still checked against the same
# publisher-provided checksum; HTML download/verification pages are rejected.
$mirrors = @(
    'netix.dl.sourceforge.net',
    'cfhcable.dl.sourceforge.net',
    'pilotfiber.dl.sourceforge.net',
    'gigenet.dl.sourceforge.net',
    'psychz.dl.sourceforge.net',
    'zenlayer.dl.sourceforge.net',
    'downloads.sourceforge.net'
)
$path = "project/portableapps/PortableApps.com%20Installer/$toolName"
# Windows has a built-in curl.exe. Resolve ONE full filesystem path rather than
# using Get-Command results directly: both the Windows and Git for Windows copies
# may be returned as an array on a hosted runner. An array expanded by the call
# operator (&) becomes one invalid command containing both paths.
$curlExe = Join-Path $env:WINDIR 'System32\curl.exe'
if (-not (Test-Path -LiteralPath $curlExe -PathType Leaf)) {
    # Only use the first application when the documented Windows copy is absent.
    $curlCommand = Get-Command -Name curl.exe -All -CommandType Application -ErrorAction Stop | Select-Object -First 1
    if ($null -eq $curlCommand) { throw 'No curl.exe application found.' }
    $curlExe = [string]$curlCommand.Source
}
if ([string]::IsNullOrWhiteSpace($curlExe) -or -not (Test-Path -LiteralPath $curlExe -PathType Leaf)) {
    throw "Cannot locate the selected curl.exe executable: $curlExe"
}
Write-Host "Downloader executable: $curlExe"
& $curlExe --version
if ($LASTEXITCODE -ne 0) { throw "curl.exe self-check failed ($LASTEXITCODE)" }
$success = $false
foreach ($mirror in $mirrors) {
    if ($mirror -notmatch '^(?:[a-z0-9-]+\.dl|downloads)\.sourceforge\.net$') {
        throw "Unapproved SourceForge hostname: $mirror"
    }
    if (Test-Path -LiteralPath $destination) { Remove-Item -LiteralPath $destination -Force }
    $url = "https://$mirror/$path"
    Write-Host "Trying official SourceForge mirror: $mirror"
    try {
        # curl.exe follows actual download redirects and supports reliable retry/timeouts.
        # No Powershell aliases, hidden windows, external download managers, or policy bypasses.
        & $curlExe --fail --location --silent --show-error --retry 2 --retry-delay 2 --connect-timeout 15 --max-time 120 --output $destination $url
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Mirror $mirror returned curl exit code $LASTEXITCODE."
            continue
        }
        if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) {
            Write-Warning "Mirror $mirror did not produce a download."
            continue
        }
        $size = (Get-Item -LiteralPath $destination).Length
        # A SourceForge HTML challenge/landing page may be served with HTTP 200.
        # Require a plausible tool size AND the exact published checksum.
        if ($size -lt 1000000 -or $size -gt 30000000) {
            Write-Warning "Mirror $mirror returned $size bytes instead of the installer (likely an HTML page)."
            continue
        }
        $actual = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expectedSha256) {
            Write-Warning "Mirror $mirror supplied an unexpected file (size $size, SHA-256 $actual). Refusing to execute it."
            continue
        }
        $stream = [System.IO.File]::OpenRead($destination)
        try {
            if ($stream.ReadByte() -ne 0x4d -or $stream.ReadByte() -ne 0x5a) {
                Write-Warning "Mirror $mirror returned a non-Windows executable."
                continue
            }
        } finally {
            $stream.Dispose()
        }
        Write-Host "Verified official PortableApps.com Installer $toolVersion from $mirror ($size bytes)."
        Write-Host "SHA-256: $actual"
        $success = $true
        break
    } catch {
        Write-Warning "Mirror $mirror unavailable: $($_.Exception.Message)"
    }
}
if (-not $success) {
    if (Test-Path -LiteralPath $destination) { Remove-Item -LiteralPath $destination -Force }
    throw 'No official SourceForge mirror returned a checksum-verified installer tool. Check HTTP failures and checksum warnings above. Build stopped safely before compilation; do NOT disable verification.'
}
