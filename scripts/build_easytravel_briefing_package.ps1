[CmdletBinding()]
param(
    [string]$Version = "0.2.1",
    [string]$DistRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$source = Join-Path $repo "packaging\easytravel-briefing-materials"
$dist = if ($DistRoot) {
    [IO.Path]::GetFullPath($DistRoot)
} else {
    Join-Path $repo "dist"
}
$stage = Join-Path $dist "EasyTravel-Briefing-Materials-$Version"
$zip = Join-Path $dist "EasyTravel-Briefing-Materials-$Version.zip"

if (-not $stage.StartsWith($dist, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe staging path."
}
if (Test-Path $stage) {
    throw "Staging path already exists; choose another destination: $stage"
}
if (Test-Path $zip) {
    throw "Package already exists; choose another destination: $zip"
}

$canonical = Join-Path $source "shared"
$codexSkill = Join-Path $source (
    "plugins\easytravel-briefing-materials\skills\" +
    "easytravel-briefing-materials"
)
$claudeSkill = Join-Path $source "claude\skills\easytravel-briefing-materials"
foreach ($skillRoot in @($codexSkill, $claudeSkill)) {
    foreach ($relative in @(
        "SKILL.md",
        "references\audio-and-template.md",
        "references\cli.md",
        "references\narration-policy.md",
        "references\sources-and-op-review.md"
    )) {
        $canonicalFile = Join-Path $canonical $relative
        $mirrorFile = Join-Path $skillRoot $relative
        if (-not (Test-Path -LiteralPath $mirrorFile -PathType Leaf)) {
            throw "Skill mirror is incomplete: $mirrorFile"
        }
        $expected = (Get-FileHash -Algorithm SHA256 -LiteralPath $canonicalFile).Hash
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $mirrorFile).Hash
        if ($actual -ne $expected) {
            throw "Skill mirror differs from canonical content: $mirrorFile"
        }
    }
}

New-Item -ItemType Directory -Force $dist | Out-Null
New-Item -ItemType Directory $stage | Out-Null

foreach ($directory in @(".agents", "plugins", "claude", "shared")) {
    Copy-Item -LiteralPath (Join-Path $source $directory) -Destination $stage -Recurse
}
foreach ($file in @("Install-EasyTravelBriefingMaterials.ps1", "INSTALL.txt")) {
    Copy-Item -LiteralPath (Join-Path $source $file) -Destination $stage
}

$app = Join-Path $stage "app"
$appSource = Join-Path $app "src"
$appScripts = Join-Path $app "scripts\briefing"
$appConfig = Join-Path $app "config"
New-Item -ItemType Directory -Force $appSource | Out-Null
New-Item -ItemType Directory -Force $appScripts | Out-Null
New-Item -ItemType Directory -Force $appConfig | Out-Null
Copy-Item -LiteralPath (Join-Path $repo "src\travel_briefing") -Destination $appSource -Recurse
foreach ($scriptName in @(
    "patch_list_template.ps1",
    "render_list_template.ps1",
    "synthesize_yating.ps1"
)) {
    Copy-Item -LiteralPath (Join-Path $repo "scripts\briefing\$scriptName") -Destination $appScripts
}
Copy-Item -LiteralPath (Join-Path $repo "config\briefing.example.toml") -Destination $appConfig
$appPyproject = Join-Path $source "app-pyproject.toml"
Copy-Item -LiteralPath $appPyproject -Destination (Join-Path $app "pyproject.toml")
Copy-Item -LiteralPath (Join-Path $source "APP-README.md") -Destination (Join-Path $app "README.md")

$generatedDirs = Get-ChildItem -LiteralPath $stage -Directory -Recurse -Force |
    Where-Object { $_.Name -eq "__pycache__" -or $_.Name -like "*.egg-info" }
foreach ($generatedDir in $generatedDirs) {
    if (-not $generatedDir.FullName.StartsWith($stage, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe generated directory path: $($generatedDir.FullName)"
    }
    Remove-Item -LiteralPath $generatedDir.FullName -Recurse -Force
}

$forbiddenExtensions = @(
    ".doc", ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".xls",
    ".csv", ".wav", ".mp3", ".srt", ".db", ".sqlite"
)
$forbiddenFiles = @(
    Get-ChildItem -LiteralPath $stage -File -Recurse -Force |
        Where-Object {
            $_.Name -like ".env*" -or
            $_.Extension.ToLowerInvariant() -in $forbiddenExtensions
        }
)
$forbiddenDirectories = @(
    Get-ChildItem -LiteralPath $stage -Directory -Recurse -Force |
        Where-Object {
            $_.Name -in @(".git", ".venv", "browser-profile", "output", "outputs", "private")
        }
)
if ($forbiddenFiles.Count -or $forbiddenDirectories.Count) {
    throw "Briefing package contains a forbidden private or generated path."
}

$requiredRelativeFiles = @(
    ".agents\plugins\marketplace.json",
    "plugins\easytravel-briefing-materials\.codex-plugin\plugin.json",
    "shared\SKILL.md",
    "claude\skills\easytravel-briefing-materials\SKILL.md",
    "app\src\travel_briefing\list_calibration.py",
    "app\config\briefing.example.toml",
    "app\scripts\briefing\patch_list_template.ps1",
    "app\scripts\briefing\render_list_template.ps1",
    "app\scripts\briefing\synthesize_yating.ps1"
)
foreach ($relativeFile in $requiredRelativeFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $stage $relativeFile) -PathType Leaf)) {
        throw "Briefing package allowlist is incomplete: $relativeFile"
    }
}

$sensitivePatterns = @(
    '(?i)azure[_-]?speech[_-]?key\s*[:=]\s*["''][^"'']+["'']',
    '(?i)(password|cookie|access[_-]?token)\s*[:=]\s*["''][^"'']+["'']',
    '(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----',
    '(?i)C:\\Users\\[^\\]+\\Downloads\\LIST-[^\s"'']+\.docx?',
    'LIST-(\d{2}|\d{4})[A-Z]{3}\d{4}[A-Z0-9]+\.docx?'
)
$textExtensions = @(
    ".json", ".md", ".ps1", ".py", ".toml", ".txt"
)
foreach ($textFile in Get-ChildItem -LiteralPath $stage -File -Recurse -Force) {
    if ($textFile.Extension.ToLowerInvariant() -notin $textExtensions) {
        continue
    }
    $content = Get-Content -LiteralPath $textFile.FullName -Raw -Encoding UTF8
    foreach ($pattern in $sensitivePatterns) {
        if ($content -match $pattern) {
            throw "Briefing package contains a sensitive-data pattern."
        }
    }
}

$archiveItems = @(
    Get-ChildItem -LiteralPath $stage -Force | ForEach-Object { $_.FullName }
)
Compress-Archive -LiteralPath $archiveItems -DestinationPath $zip -CompressionLevel Optimal
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zip).Hash.ToLowerInvariant()
$entries = (Get-ChildItem -LiteralPath $stage -File -Recurse -Force).Count
Write-Output "package=$zip"
Write-Output "sha256=$hash"
Write-Output "entries=$entries"
Write-Output "stage=$stage"
