[CmdletBinding()]
param(
    [string]$OutputRoot = "",
    [string]$MasterPath = "",
    [string]$CalibrationManifestPath = "",
    [string]$PdftoppmPath = "",
    [string]$FfmpegPath = "",
    [switch]$SkipCodexPluginInstall,
    [switch]$SkipClaudeSkillInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $env:LOCALAPPDATA) { throw "LOCALAPPDATA is not available." }
if (-not $env:USERPROFILE) { throw "USERPROFILE is not available." }

$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceApp = Join-Path $packageRoot "app"
$sourceMarketplace = $packageRoot
$sourceClaudeSkill = Join-Path $packageRoot "claude\skills\easytravel-briefing-materials"
if (-not (Test-Path (Join-Path $sourceApp "pyproject.toml"))) {
    throw "Package is incomplete: app\pyproject.toml is missing."
}
if (-not (Test-Path (Join-Path $packageRoot ".agents\plugins\marketplace.json"))) {
    throw "Package is incomplete: marketplace manifest is missing."
}
if (-not (Test-Path (Join-Path $sourceClaudeSkill "SKILL.md"))) {
    throw "Package is incomplete: Claude Skill is missing."
}

$python = $null
$pythonPrefix = @()
$versionCheck = "import sys; raise SystemExit(" +
    "0 if sys.version_info >= (3,12) else 1)"
$py = Get-Command py.exe -ErrorAction SilentlyContinue
if ($py) {
    & $py.Source -3 -c $versionCheck
    if ($LASTEXITCODE -eq 0) {
        $python = $py.Source
        $pythonPrefix = @("-3")
    }
}
if (-not $python) {
    $candidate = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($candidate) {
        & $candidate.Source -c $versionCheck
        if ($LASTEXITCODE -eq 0) { $python = $candidate.Source }
    }
}
if (-not $python) {
    throw "Python 3.12 or newer is required. Install it, then rerun this installer."
}

$installRoot = Join-Path $env:LOCALAPPDATA "EasyTravelBriefing"
$appRoot = Join-Path $installRoot "app"
$marketplaceRoot = Join-Path $installRoot "marketplace"
$configPath = Join-Path $installRoot "config.toml"
if (Test-Path $configPath) {
    throw (
        "LIST_RECALIBRATION_REQUIRED: existing 0.1 config must be backed up " +
        "and replaced with calibrated master/manifest configuration."
    )
}
if (Test-Path $appRoot) {
    throw "EasyTravelBriefing app already exists; preserve it and review before reinstalling."
}

if (-not $SkipClaudeSkillInstall) {
    $claudeSkillRoot = Join-Path $env:USERPROFILE ".claude\skills\easytravel-briefing-materials"
    if (Test-Path $claudeSkillRoot) {
        throw "Claude Skill already exists; preserve it or use -SkipClaudeSkillInstall."
    }
}

$configText = $null
if (-not (Test-Path $configPath)) {
    if (-not $OutputRoot) {
        $OutputRoot = Read-Host "Local briefing output root"
    }
    if (-not $MasterPath) {
        $MasterPath = Read-Host "Private calibrated LIST-master.docx path"
    }
    if (-not $CalibrationManifestPath) {
        $CalibrationManifestPath = Read-Host "Private calibration-manifest.json path"
    }
    if (-not $PdftoppmPath) {
        $pdftoppm = Get-Command pdftoppm.exe -ErrorAction SilentlyContinue
        if (-not $pdftoppm) {
            $pdftoppm = Get-Command pdftoppm -ErrorAction SilentlyContinue
        }
        if ($pdftoppm) {
            $PdftoppmPath = $pdftoppm.Source
        } else {
            $PdftoppmPath = Read-Host "Existing pdftoppm executable path"
        }
    }

    foreach ($requiredPath in @(
        @{ Name = "OutputRoot"; Value = $OutputRoot },
        @{ Name = "MasterPath"; Value = $MasterPath },
        @{ Name = "CalibrationManifestPath"; Value = $CalibrationManifestPath },
        @{ Name = "PdftoppmPath"; Value = $PdftoppmPath }
    )) {
        if ([string]::IsNullOrWhiteSpace($requiredPath.Value)) {
            throw "$($requiredPath.Name) must not be blank."
        }
    }

    $resolvedOutput = [IO.Path]::GetFullPath(
        [Environment]::ExpandEnvironmentVariables($OutputRoot)
    )
    $resolvedMaster = [IO.Path]::GetFullPath(
        [Environment]::ExpandEnvironmentVariables($MasterPath)
    )
    $resolvedCalibrationManifest = [IO.Path]::GetFullPath(
        [Environment]::ExpandEnvironmentVariables($CalibrationManifestPath)
    )
    $resolvedPdftoppm = [IO.Path]::GetFullPath(
        [Environment]::ExpandEnvironmentVariables($PdftoppmPath)
    )
    if (Test-Path -LiteralPath $resolvedOutput -PathType Leaf) {
        throw "OutputRoot must identify a directory, not a file."
    }
    if ([IO.Path]::GetExtension($resolvedMaster).ToLowerInvariant() -ne ".docx") {
        throw "MasterPath must identify a DOCX file."
    }
    if (-not (Test-Path -LiteralPath $resolvedMaster -PathType Leaf)) {
        throw "MasterPath does not exist."
    }
    if (
        [IO.Path]::GetExtension($resolvedCalibrationManifest).ToLowerInvariant() -ne ".json" -or
        -not (Test-Path -LiteralPath $resolvedCalibrationManifest -PathType Leaf)
    ) {
        throw "CalibrationManifestPath must identify an existing JSON file."
    }
    if (-not (Test-Path -LiteralPath $resolvedPdftoppm -PathType Leaf)) {
        throw "PdftoppmPath does not exist."
    }
    try {
        $calibration = Get-Content `
            -LiteralPath $resolvedCalibrationManifest `
            -Raw `
            -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        throw "LIST_RECALIBRATION_REQUIRED: calibration manifest is invalid."
    }
    if (
        [int]$calibration.schema_version -ne 2 -or
        [string]$calibration.generator_version -cne "list-calibration/2" -or
        [string]$calibration.master_sha256 -notmatch "^[0-9a-f]{64}$" -or
        [string]$calibration.master_sha256 -match "^0{64}$" -or
        [string]$calibration.master_structure_fingerprint -notmatch "^[0-9a-f]{64}$"
    ) {
        throw "LIST_RECALIBRATION_REQUIRED: unsupported calibration manifest."
    }
    $actualMasterHash = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $resolvedMaster
    ).Hash.ToLowerInvariant()
    if ($actualMasterHash -cne [string]$calibration.master_sha256) {
        throw "LIST_RECALIBRATION_REQUIRED: LIST master hash changed."
    }
    if (
        [IO.Path]::GetDirectoryName($resolvedMaster) -cne
        [IO.Path]::GetDirectoryName($resolvedCalibrationManifest)
    ) {
        throw "LIST master and calibration manifest must share one private directory."
    }
    if (
        $resolvedOutput.StartsWith(
            [IO.Path]::GetDirectoryName($resolvedMaster),
            [StringComparison]::OrdinalIgnoreCase
        ) -or
        $resolvedMaster.StartsWith(
            $resolvedOutput,
            [StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw "LIST private directory must be outside OutputRoot."
    }

    function ConvertTo-TomlPath([string]$Value) {
        return $Value.Replace("\", "\\").Replace('"', '\"')
    }

    $configLines = @(
        "[output]",
        "root = `"$(ConvertTo-TomlPath $resolvedOutput)`"",
        "",
        "[template]",
        "master_path = `"$(ConvertTo-TomlPath $resolvedMaster)`"",
        "calibration_manifest = `"$(ConvertTo-TomlPath $resolvedCalibrationManifest)`"",
        "",
        "[tools]",
        "pdftoppm = `"$(ConvertTo-TomlPath $resolvedPdftoppm)`""
    )
    if ($FfmpegPath) {
        $resolvedFfmpeg = [IO.Path]::GetFullPath(
            [Environment]::ExpandEnvironmentVariables($FfmpegPath)
        )
        if (-not (Test-Path -LiteralPath $resolvedFfmpeg -PathType Leaf)) {
            throw "FfmpegPath does not exist."
        }
        $configLines += "ffmpeg = `"$(ConvertTo-TomlPath $resolvedFfmpeg)`""
    }
    $configText = ($configLines -join "`n") + "`n"
}

New-Item -ItemType Directory -Force $installRoot | Out-Null
New-Item -ItemType Directory $appRoot | Out-Null
New-Item -ItemType Directory $marketplaceRoot | Out-Null
Copy-Item -Path (Join-Path $sourceApp "*") -Destination $appRoot -Recurse
Copy-Item -Path (Join-Path $sourceMarketplace ".agents") -Destination $marketplaceRoot -Recurse
Copy-Item -Path (Join-Path $sourceMarketplace "plugins") -Destination $marketplaceRoot -Recurse

$venv = Join-Path $appRoot ".venv"
& $python @pythonPrefix -m venv $venv
if ($LASTEXITCODE -ne 0) {
    throw "Could not create the EasyTravel briefing virtual environment."
}
$venvPython = Join-Path $venv "Scripts\python.exe"
& $venvPython -m pip install --disable-pip-version-check -e $appRoot
if ($LASTEXITCODE -ne 0) {
    throw "Could not install EasyTravel briefing dependencies."
}

if ($null -ne $configText) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($configPath, $configText, $utf8NoBom)
}

if (-not $SkipCodexPluginInstall) {
    $codex = Get-Command codex.exe -ErrorAction SilentlyContinue
    if (-not $codex) { $codex = Get-Command codex -ErrorAction SilentlyContinue }
    if (-not $codex) {
        throw "Codex CLI is required unless -SkipCodexPluginInstall is used."
    }
    & $codex.Source plugin marketplace add $marketplaceRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Could not register the local EasyTravel briefing marketplace."
    }
    & $codex.Source plugin add "easytravel-briefing-materials@easytravel-briefing-local"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install the EasyTravel briefing plugin."
    }
}

if (-not $SkipClaudeSkillInstall) {
    $claudeSkills = Join-Path $env:USERPROFILE ".claude\skills"
    New-Item -ItemType Directory -Force $claudeSkills | Out-Null
    Copy-Item -LiteralPath $sourceClaudeSkill -Destination $claudeSkills -Recurse
}

& $venvPython -m travel_briefing.cli doctor --format text
if ($LASTEXITCODE -ne 0) { throw "EasyTravel briefing doctor failed." }

Write-Host ""
Write-Host "EasyTravel Briefing Materials installed successfully."
Write-Host "Runtime: $appRoot"
Write-Host "Config:  $configPath"
Write-Host "Open a new agent conversation and use easytravel-briefing-materials."
