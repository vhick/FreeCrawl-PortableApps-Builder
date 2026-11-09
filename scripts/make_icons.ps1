$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$iconFile = Join-Path $repo 'work/upstream/apps/desktop/resources/icon.ico'
if (-not (Test-Path -LiteralPath $iconFile -PathType Leaf)) { throw 'Verified upstream ICO is absent.' }
foreach ($size in @(16, 32)) {
  $icon = [System.Drawing.Icon]::new($iconFile, [System.Drawing.Size]::new($size, $size))
  try {
    $bmp = $icon.ToBitmap()
    try {
      $destination = Join-Path $repo "work/icon_$size.png"
      $bmp.Save($destination, [System.Drawing.Imaging.ImageFormat]::Png)
      if ((Get-Item -LiteralPath $destination).Length -lt 100) { throw "PNG is too small: $destination" }
      Write-Host "Generated $destination from verified upstream icon"
    } finally { $bmp.Dispose() }
  } finally { $icon.Dispose() }
}
Copy-Item -LiteralPath $iconFile -Destination (Join-Path $repo 'launcher/icon.ico') -Force
