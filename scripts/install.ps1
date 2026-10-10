param([switch]$Dev)
. "$PSScriptRoot\common.ps1"
Push-Location $RepoRoot
try {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCommand) { throw 'Install Python 3.10+ and add it to PATH.' }
    & $PythonCommand.Source -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required.' }
    if (-not (Test-Path -LiteralPath $SentinelPython)) {
        & $PythonCommand.Source -m venv (Join-Path $RepoRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    }
    $InstallTarget = '.'
    if ($Dev) { $InstallTarget = '.[dev]' }
    & $SentinelPython -m pip install $InstallTarget
    if ($LASTEXITCODE -ne 0) { throw 'Package installation failed.' }
    if (-not (Test-Path -LiteralPath $SentinelConfig)) {
        Copy-Item -LiteralPath (Join-Path $RepoRoot 'config\sentinel.example.json') -Destination $SentinelConfig
    }
    & $SentinelPython -m agent_sentinel --config $SentinelConfig validate
    if ($LASTEXITCODE -ne 0) { throw 'Configuration validation failed.' }
    & $SentinelPython -m agent_sentinel --config $SentinelConfig status
    if ($LASTEXITCODE -ne 0) { throw 'Startup self-check failed.' }
    Write-Output 'Installed. Configure Antigravity using docs/ANTIGRAVITY.md. Review configuration.dry_run in the status above; existing settings are preserved.'
} finally { Pop-Location }
