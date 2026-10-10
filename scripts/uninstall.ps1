. "$PSScriptRoot\common.ps1"
Assert-SentinelInstalled
& "$PSScriptRoot\stop.ps1"
if ((Get-SentinelStatus).running) { throw 'Stop watchdog before uninstalling.' }
& $SentinelPython -m pip uninstall --yes agent-sentinel
if ($LASTEXITCODE -ne 0) { throw 'Uninstall failed.' }
Write-Output 'Package removed. Config, runtime data and venv retained. Remove any AI Agent Watchdog hooks/sidecar entries you added to Antigravity.'
