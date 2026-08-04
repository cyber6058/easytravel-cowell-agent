[CmdletBinding()]
param(
    [string]$CowellBaseUrl = "",
    [switch]$SkipPluginInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $env:LOCALAPPDATA) { throw "LOCALAPPDATA is not available." }
if (-not $env:USERPROFILE) { throw "USERPROFILE is not available." }

$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceApp = Join-Path $packageRoot "app"
$sourceMarketplace = $packageRoot
if (-not (Test-Path (Join-Path $sourceApp "pyproject.toml"))) {
    throw "Package is incomplete: app\pyproject.toml is missing."
}
if (-not (Test-Path (Join-Path $packageRoot ".agents\plugins\marketplace.json"))) {
    throw "Package is incomplete: marketplace manifest is missing."
}

$python = $null
$pythonPrefix = @()
$py = Get-Command py.exe -ErrorAction SilentlyContinue
if ($py) {
    & $py.Source -3.12 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)"
    if ($LASTEXITCODE -eq 0) {
        $python = $py.Source
        $pythonPrefix = @("-3.12")
    }
}
if (-not $python) {
    $candidate = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($candidate) {
        & $candidate.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)"
        if ($LASTEXITCODE -eq 0) { $python = $candidate.Source }
    }
}
if (-not $python) {
    throw "Python 3.12 or newer is required. Install it, then rerun this installer."
}

$chrome86 = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
$chrome64 = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (
    -not (Get-Command chrome.exe -ErrorAction SilentlyContinue) -and
    -not (Test-Path $chrome86) -and
    -not (Test-Path $chrome64)
) {
    throw "Google Chrome is required. Install it, then rerun this installer."
}

$installRoot = Join-Path $env:LOCALAPPDATA "EasyTravelCowellCLI"
$appRoot = Join-Path $installRoot "app"
$marketplaceRoot = Join-Path $installRoot "marketplace"
$templatesRoot = Join-Path $installRoot "templates"
New-Item -ItemType Directory -Force $installRoot | Out-Null
New-Item -ItemType Directory -Force $appRoot | Out-Null
New-Item -ItemType Directory -Force $marketplaceRoot | Out-Null
New-Item -ItemType Directory -Force $templatesRoot | Out-Null
Copy-Item -Path (Join-Path $sourceApp "*") -Destination $appRoot -Recurse -Force
Copy-Item -Path (Join-Path $sourceMarketplace ".agents") -Destination $marketplaceRoot -Recurse -Force
Copy-Item -Path (Join-Path $sourceMarketplace "plugins") -Destination $marketplaceRoot -Recurse -Force

$venv = Join-Path $appRoot ".venv"
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
    & $python @pythonPrefix -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the EasyTravel Cowell CLI virtual environment."
    }
}
$venvPython = Join-Path $venv "Scripts\python.exe"
& $venvPython -m pip install --disable-pip-version-check -e $appRoot
if ($LASTEXITCODE -ne 0) { throw "Could not install Cowell CLI dependencies." }

$configRoot = Join-Path $env:LOCALAPPDATA "CowellCLI"
$configPath = Join-Path $configRoot "config.toml"
New-Item -ItemType Directory -Force $configRoot | Out-Null
if (-not (Test-Path $configPath)) {
    if (-not $CowellBaseUrl) {
        $CowellBaseUrl = Read-Host "Cowell HTTPS base URL (example: https://cowell.example.com/)"
    }
    $uri = $null
    if (
        -not [Uri]::TryCreate($CowellBaseUrl, [UriKind]::Absolute, [ref]$uri) -or
        $uri.Scheme -ne "https"
    ) {
        throw "CowellBaseUrl must be an absolute HTTPS URL."
    }
    $normalized = $CowellBaseUrl.TrimEnd("/") + "/"
    $config = @"
[cowell]
base_url = "$normalized"
browser_profile = "%LOCALAPPDATA%\\CowellCLI\\browser-profile"

[storage]
database = "%LOCALAPPDATA%\\CowellCLI\\cowell.db"
"@
    Set-Content -Path $configPath -Value $config -Encoding utf8
}

$launcher = Join-Path $installRoot "Start-CowellBrowser.ps1"
Copy-Item -Path (Join-Path $appRoot "scripts\discovery\launch_browser.ps1") -Destination $launcher -Force

if (-not $SkipPluginInstall) {
    $codex = Get-Command codex.exe -ErrorAction SilentlyContinue
    if (-not $codex) { $codex = Get-Command codex -ErrorAction SilentlyContinue }
    if (-not $codex) {
        throw "Codex CLI is required to install the easytravel-cowell-cli plugin."
    }
    & $codex.Source plugin marketplace add $marketplaceRoot
    $marketplaceResult = $LASTEXITCODE
    & $codex.Source plugin add "easytravel-cowell-cli@easytravel-local"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install easytravel-cowell-cli (marketplace add exit: $marketplaceResult)."
    }
}

& $venvPython -m cowell_cli.cli doctor --format text
if ($LASTEXITCODE -ne 0) { throw "Cowell CLI doctor failed." }

Write-Host ""
Write-Host "EasyTravel Cowell CLI installed successfully."
Write-Host "1. Run: powershell -NoProfile -ExecutionPolicy Bypass -File `"$launcher`""
Write-Host "2. Log in to Cowell in that controlled Chrome window."
Write-Host "3. For rooming, provide group code, order ID, and a DOCX/XLSX file. Cabin is optional."
Write-Host "4. For passports, provide the PDF/photo source and desired output folder."
Write-Host "Runtime:   $appRoot"
Write-Host "Config:    $configPath"
Write-Host "Templates: $templatesRoot"
