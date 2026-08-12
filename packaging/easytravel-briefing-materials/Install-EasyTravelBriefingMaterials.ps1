[CmdletBinding()]
param(
    [string]$OutputRoot = "",
    [string]$TemplatePath = "",
    [string]$TemplateLayoutFingerprint = "",
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
    if (-not $TemplatePath) {
        $TemplatePath = Read-Host "Private LIST DOC or DOCX path"
    }
    if (-not $TemplateLayoutFingerprint) {
        $TemplateLayoutFingerprint = Read-Host "Approved LIST layout SHA-256"
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
        @{ Name = "TemplatePath"; Value = $TemplatePath },
        @{ Name = "PdftoppmPath"; Value = $PdftoppmPath }
    )) {
        if ([string]::IsNullOrWhiteSpace($requiredPath.Value)) {
            throw "$($requiredPath.Name) must not be blank."
        }
    }

    $resolvedOutput = [IO.Path]::GetFullPath(
        [Environment]::ExpandEnvironmentVariables($OutputRoot)
    )
    $resolvedTemplate = [IO.Path]::GetFullPath(
        [Environment]::ExpandEnvironmentVariables($TemplatePath)
    )
    $resolvedPdftoppm = [IO.Path]::GetFullPath(
        [Environment]::ExpandEnvironmentVariables($PdftoppmPath)
    )
    if (Test-Path -LiteralPath $resolvedOutput -PathType Leaf) {
        throw "OutputRoot must identify a directory, not a file."
    }
    if ([IO.Path]::GetExtension($resolvedTemplate) -notin ".doc", ".docx") {
        throw "TemplatePath must identify a DOC or DOCX file."
    }
    if (-not (Test-Path -LiteralPath $resolvedTemplate -PathType Leaf)) {
        throw "TemplatePath does not exist."
    }
    if (-not (Test-Path -LiteralPath $resolvedPdftoppm -PathType Leaf)) {
        throw "PdftoppmPath does not exist."
    }
    $fingerprint = $TemplateLayoutFingerprint.Trim().ToLowerInvariant()
    if ($fingerprint -notmatch "^[0-9a-f]{64}$" -or $fingerprint -match "^0{64}$") {
        throw "TemplateLayoutFingerprint must be an approved non-placeholder SHA-256."
    }

    function ConvertTo-TomlPath([string]$Value) {
        return $Value.Replace("\", "\\").Replace('"', '\"')
    }

    $configLines = @(
        "[output]",
        "root = `"$(ConvertTo-TomlPath $resolvedOutput)`"",
        "",
        "[template]",
        "path = `"$(ConvertTo-TomlPath $resolvedTemplate)`"",
        "layout_fingerprint = `"$fingerprint`"",
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
