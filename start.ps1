$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$lanePython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $lanePython)) {
    Write-Host 'Run setup.ps1 once to install the local environment.'
    exit 1
}
& $lanePython run.py
