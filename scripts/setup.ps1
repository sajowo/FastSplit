$ErrorActionPreference = 'Stop'

Set-Location (Join-Path $PSScriptRoot '..')

$VenvDir = if ($env:FASTSPLIT_VENV_DIR) { $env:FASTSPLIT_VENV_DIR } else { Join-Path $HOME ".venvs\fastsplit" }

if (-not (Test-Path $VenvDir)) {
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $VenvDir) | Out-Null
  try {
    py -3.11 -m venv $VenvDir
  } catch {
    py -3 -m venv $VenvDir
  }
}

& (Join-Path $VenvDir "Scripts\python.exe") -m pip install -U pip | Out-Null
& (Join-Path $VenvDir "Scripts\python.exe") -m pip install -r requirements.txt | Out-Null

if (-not (Test-Path '.\static')) {
  New-Item -ItemType Directory -Path .\static | Out-Null
}

& (Join-Path $VenvDir "Scripts\python.exe") manage.py migrate
Write-Output "OK: environment ready"
