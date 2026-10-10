. "$PSScriptRoot\common.ps1"
Assert-SentinelInstalled
& $SentinelPython -m agent_sentinel --config $SentinelConfig stop
if ($LASTEXITCODE -ne 0) { throw 'Stop request failed.' }
for ($Attempt = 0; $Attempt -lt 45; $Attempt++) {
    if (-not (Get-SentinelStatus).running) { Write-Output 'Watchdog stopped.'; exit 0 }
    Start-Sleep -Seconds 1
}
throw 'Watchdog is still completing a check. Retry status after the configured agentapi timeout.'
