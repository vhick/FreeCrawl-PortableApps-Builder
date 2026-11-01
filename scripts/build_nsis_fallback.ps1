# A TRANSPARENT, independent NSIS-built installer fallback. Not official PA.c Installer output.
param([Parameter(Mandatory=$true)][string]$Version,[Parameter(Mandatory=$true)][string]$Revision)
$ErrorActionPreference='Stop'
$stage=(Resolve-Path 'stage/FreeCrawlPortable').Path
$target=Join-Path (Resolve-Path 'dist').Path "FreeCrawlPortable_v${Version}_r${Revision}_win64.paf.exe"
if (Test-Path -LiteralPath $target) { throw "Refusing to overwrite PAF: $target" }
foreach ($rel in @('FreeCrawlPortable.exe','App/AppInfo/appinfo.ini','App/AppInfo/appicon.ico','App/FreeCrawl/FreeCrawl SEO Tool.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $stage $rel) -PathType Leaf)) { throw "Staging file missing: $rel" }
}
# windows-2022 includes NSIS in the runner image; do not install third-party
# Chocolatey packages unless the hosted runner image actually loses NSIS.
$makensis=$null
foreach ($path in @("${env:ProgramFiles(x86)}\NSIS\makensis.exe", "${env:ProgramFiles}\NSIS\makensis.exe")) {
    if (Test-Path -LiteralPath $path -PathType Leaf) { $makensis=$path; break }
}
if (-not $makensis) {
    $cmd=Get-Command 'makensis.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) { $makensis=$cmd.Source }
}
if (-not $makensis) { throw 'NSIS makensis.exe missing on windows-2022 image. Install a verified NSIS compiler or use the official builder.' }
Write-Host "NSIS version: $(& $makensis /VERSION)"
Write-Warning 'Using independent NSIS PAF-style installer fallback. This is NOT an official PortableApps.com Installer-built or certified release.'
$script=(Resolve-Path 'installer/FreeCrawlPortable.nsi').Path
$info=[System.Diagnostics.ProcessStartInfo]::new($makensis)
$info.UseShellExecute=$false
$info.WorkingDirectory=(Get-Location).Path
$info.RedirectStandardOutput=$true
$info.RedirectStandardError=$true
foreach ($arg in @('/V2', "/DSTAGE_DIR=$stage", "/DOUTPUT_FILE=$target", "/DAPP_VERSION=$Version", $script)) { [void]$info.ArgumentList.Add($arg) }
$proc=[System.Diagnostics.Process]::Start($info)
if (-not $proc) { throw 'Could not run NSIS compiler' }
try {
    $stdout=$proc.StandardOutput.ReadToEndAsync()
    $stderr=$proc.StandardError.ReadToEndAsync()
    if (-not $proc.WaitForExit(720000)) {
        try { $proc.Kill($true) } catch { $proc.Kill() }
        throw 'NSIS installer compile exceeded 12 minutes'
    }
    [System.Threading.Tasks.Task]::WaitAll(@($stdout,$stderr))
    Write-Host $stdout.Result
    if ($stderr.Result) { Write-Warning $stderr.Result }
    if ($proc.ExitCode -ne 0) { throw "NSIS compilation failed ($($proc.ExitCode))." }
} finally { $proc.Dispose() }
if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw 'NSIS returned success but PAF file is missing' }
Write-Host "Independent NSIS fallback created: $target"
