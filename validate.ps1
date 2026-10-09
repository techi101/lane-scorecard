param([switch]$Browser)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$lanePython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $lanePython)) { throw 'Run setup.ps1 first.' }
$laneValidationArgs = @('scripts/validate.py')
if ($Browser) { $laneValidationArgs += '--browser' }
& $lanePython @laneValidationArgs
exit $LASTEXITCODE
