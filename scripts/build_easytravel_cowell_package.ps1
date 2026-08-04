[CmdletBinding()]
param(
    [string]$Version = "0.3.2"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$source = Join-Path $repo "packaging\easytravel-cowell-cli"
$dist = Join-Path $repo "dist"
$stage = Join-Path $dist "EasyTravel-Cowell-CLI-$Version"
$zip = Join-Path $dist "EasyTravel-Cowell-CLI-$Version.zip"

if (-not $stage.StartsWith($dist, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe staging path."
}
if (Test-Path $stage) {
    throw "Staging path already exists; choose another version: $stage"
}
if (Test-Path $zip) {
    throw "Package already exists; choose another version: $zip"
}

New-Item -ItemType Directory -Force $dist | Out-Null
New-Item -ItemType Directory $stage | Out-Null

Copy-Item -Path (Join-Path $source ".agents") -Destination $stage -Recurse
Copy-Item -Path (Join-Path $source "plugins") -Destination $stage -Recurse
Copy-Item -Path (Join-Path $source "Install-EasyTravelCowellCLI.ps1") -Destination $stage
Copy-Item -Path (Join-Path $source "INSTALL.txt") -Destination $stage

$app = Join-Path $stage "app"
New-Item -ItemType Directory $app | Out-Null
Copy-Item -Path (Join-Path $repo "src") -Destination $app -Recurse
Copy-Item -Path (Join-Path $repo "config") -Destination $app -Recurse
New-Item -ItemType Directory -Force (Join-Path $app "scripts\discovery") | Out-Null
Copy-Item -Path (Join-Path $repo "scripts\discovery\launch_browser.ps1") -Destination (Join-Path $app "scripts\discovery")
Copy-Item -Path (Join-Path $repo "pyproject.toml") -Destination $app
Copy-Item -Path (Join-Path $source "APP-README.md") -Destination (Join-Path $app "README.md")

$generatedDirs = Get-ChildItem -LiteralPath $app -Directory -Recurse -Force |
    Where-Object { $_.Name -eq "__pycache__" -or $_.Name -like "*.egg-info" }
foreach ($generatedDir in $generatedDirs) {
    if (-not $generatedDir.FullName.StartsWith($app, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe generated directory path: $($generatedDir.FullName)"
    }
    Remove-Item -LiteralPath $generatedDir.FullName -Recurse -Force
}

Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip -CompressionLevel Optimal
$hash = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToLowerInvariant()
Write-Output "package=$zip"
Write-Output "sha256=$hash"
Write-Output "stage=$stage"
