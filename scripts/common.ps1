$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$SentinelPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$SentinelConfig = Join-Path $RepoRoot 'config\sentinel.json'

function Assert-SentinelInstalled {
    if (-not (Test-Path -LiteralPath $SentinelPython)) { throw 'Run scripts/install.ps1 first.' }
    if (-not (Test-Path -LiteralPath $SentinelConfig)) { throw 'Missing config/sentinel.json.' }
}

function Get-SentinelStatus {
    Assert-SentinelInstalled
    $output = & $SentinelPython -m agent_sentinel --config $SentinelConfig status
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect watchdog status.' }
    return ($output | ConvertFrom-Json)
}
