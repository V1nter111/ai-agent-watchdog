. "$PSScriptRoot\common.ps1"
$Status = Get-SentinelStatus
if ($Status.running) { Write-Output 'Watchdog is already running.'; exit 0 }
$Arguments = '-m agent_sentinel --config "' + $SentinelConfig + '" run'
$Process = Start-Process -FilePath $SentinelPython -ArgumentList $Arguments -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru
for ($Attempt = 0; $Attempt -lt 20; $Attempt++) {
    Start-Sleep -Milliseconds 250
    $Status = Get-SentinelStatus
    if ($Status.running) { Write-Output 'Watchdog started. Run scripts/status.ps1 to inspect provider readiness.'; exit 0 }
    if ($Process.HasExited) { throw 'Watchdog exited during startup. Check configuration and .sentinel/sentinel.log.' }
}
throw 'Watchdog did not become ready within five seconds.'
