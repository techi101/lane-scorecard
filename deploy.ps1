param(
    [string]$Profile = '',
    [ValidatePattern('^[a-zA-Z][a-zA-Z0-9-]{0,127}$')]
    [string]$StackName = 'lane-scorecard',
    [switch]$BuildOnly
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$lanePython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $lanePython)) { throw 'Run setup.ps1 first.' }
foreach ($laneTool in @('sam', 'docker')) {
    if (-not (Get-Command $laneTool -ErrorAction SilentlyContinue)) { throw "$laneTool is missing. Follow docs/AWS.md." }
}
if (-not $BuildOnly) {
    $laneDoctorArgs = @('scripts/doctor.py', '--aws')
    if ($Profile) { $laneDoctorArgs += @('--profile', $Profile) }
    & $lanePython @laneDoctorArgs
    if ($LASTEXITCODE -ne 0) { throw 'Deployment prerequisites are incomplete.' }
}
& $lanePython scripts/prepare_aws.py
if ($LASTEXITCODE -ne 0) { throw 'Source staging failed.' }
& sam validate --lint --region us-east-1
if ($LASTEXITCODE -ne 0) { throw 'Template validation failed.' }
& sam build --use-container
if ($LASTEXITCODE -ne 0) { throw 'Linux Lambda build failed.' }
if ($BuildOnly) { Write-Host 'Build finished. No deployment was requested.'; exit 0 }
$laneDeployArgs = @('deploy', '--guided', '--confirm-changeset', '--region', 'us-east-1', '--stack-name', $StackName)
if ($Profile) { $laneDeployArgs += @('--profile', $Profile) }
Write-Host 'Enter a fresh operator code in the SAM prompt. Keep EnableAI=0 for the first deployment.'
& sam @laneDeployArgs
if ($LASTEXITCODE -ne 0) { throw 'Deployment did not finish successfully.' }
