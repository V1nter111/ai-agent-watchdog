. "$PSScriptRoot\common.ps1"
$Status = Get-SentinelStatus
$Status | ConvertTo-Json -Depth 5
