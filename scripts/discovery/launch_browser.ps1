# Launch a dedicated, isolated Chrome for Cowell Discovery with CDP enabled.
# Separate user-data-dir from daily Chrome. The USER logs in by hand; no
# credential ever passes through the agent.
$ErrorActionPreference = 'Stop'

$chrome = 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
if (-not (Test-Path $chrome)) { $chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe' }

$profile = "$env:LOCALAPPDATA\CowellCLI\browser-profile"
New-Item -ItemType Directory -Force $profile | Out-Null

Start-Process -FilePath $chrome -ArgumentList @(
  "--remote-debugging-port=9333",
  "--user-data-dir=$profile",
  '--no-first-run',
  '--no-default-browser-check',
  'about:blank'
)

$ok = $null
for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Milliseconds 500
  try { $ok = Invoke-RestMethod -Uri "http://127.0.0.1:9333/json/version" -TimeoutSec 2 } catch {}
  if ($ok) { break }
}
if ($ok) { Write-Host "CDP ready: $($ok.Browser)" } else { Write-Host "CDP NOT available" }
