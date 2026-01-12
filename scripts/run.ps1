Param(
  [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

Set-Location (Join-Path $PSScriptRoot '..')
& .\scripts\setup.ps1 | Out-Null
$VenvDir = if ($env:FASTSPLIT_VENV_DIR) { $env:FASTSPLIT_VENV_DIR } else { Join-Path $HOME ".venvs\fastsplit" }
& (Join-Path $VenvDir "Scripts\python.exe") manage.py runserver $Port
