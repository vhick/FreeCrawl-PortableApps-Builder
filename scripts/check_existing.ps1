param(
    [Parameter(Mandatory=$true)][string]$Tag,
    [Parameter(Mandatory=$true)][string]$PackageName,
    [Parameter(Mandatory=$true)][string]$PafName
)
$ErrorActionPreference='Stop'
$repo=$env:GITHUB_REPOSITORY
if (-not $repo) { throw 'Missing caller repository' }
$result = & gh release view $Tag --repo $repo --json body,assets,isDraft,isImmutable,tagName 2>&1
if ($LASTEXITCODE -ne 0) {
    $message=($result | Out-String)
    if ($message -notmatch '(?i)(not found|HTTP 404|release not found)') { throw "Could not query existing release: $message" }
    'skip_build=false' | Out-File $env:GITHUB_OUTPUT -Append -Encoding utf8
    Write-Host 'No release yet; building both packages.'
    exit 0
}
$existing=($result | Out-String) | ConvertFrom-Json
if ($existing.isDraft) { throw 'A draft release already owns this tag; review it manually.' }
if ($existing.body -notlike '*<!-- portable-release-publisher:managed:v2 -->*') {
    throw 'Tag already belongs to a release not recognized as publisher-managed. Refusing overwrite.'
}
$assets=@($existing.assets | ForEach-Object {$_.name})
$required=@($PackageName,$PafName,'SHA256SUMS.txt')
if ($assets.Count -ne 3 -or @($required | Where-Object {$assets -notcontains $_}).Count -gt 0) {
    throw "Existing release $Tag has different assets. Refusing to overwrite; increment builder revision for new packaging."
}
# Names + publisher marker indicate this exact release was previously published. The publisher
# independently verifies downloaded checksum manifests when encountering an existing release.
'skip_build=true' | Out-File $env:GITHUB_OUTPUT -Append -Encoding utf8
Write-Host "Release $Tag already has the PAF, ZIP, and checksum file. Skipping duplicate compilation."
