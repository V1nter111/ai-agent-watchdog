# AI Agent Watchdog troubleshooting

| Symptom | Check and action |
| --- | --- |
| ConfigError / validation fails | Run validate; compare JSON keys/types with the example. Check state age is greater than stale/tool grace. |
| provider_check_failed | Create/enable the hook state source; check directory permissions. No recovery is sent on an unreadable source. |
| agentapi_available=false | Prefer the Antigravity sidecar environment, or configure the correct Antigravity executable. Ordinary shells may lack its injected PATH. |
| checked=0 | Enable hooks and run a new harmless conversation step. Expired, malformed or duplicate snapshots are excluded. |
| would_recover but no message | Dry-run is enabled by default. Validate observations before enabling live mode. |
| recovery_suppressed | Cooldown or the persisted attempt limit applies. Check whether actual progress resumed. |
| recovery_failed | Confirm agentapi works in the same environment and the conversation exists. Failed sends consume attempts; output is suppressed to avoid leaking private data. |
| No recovery for a long tool | Tool grace, process_alive=true or insufficient confirmation can suppress a send. This is expected. |
| False suspicion during long work | Increase tool_grace_seconds; use trusted process liveness/heartbeat snapshots. |
| Runtime is already locked | Stop the existing instance. OS locks release after crashes; deleting lock files while active can defeat duplicate protection on some platforms. |
| Invalid recovery ledger | Stop AI Agent Watchdog, privately inspect or back up recovery.json and correct it. Do not silently reset limits. |
| Stop takes time | An in-flight send can run up to command_timeout_seconds; several conversations can extend a check. No agent process is killed. |
| Hook command fails after moving repo | Reinstall package and regenerate integration files; update the Antigravity entries. |
| Permission prompt from optional PreToolUse | Its ask decision preserves grants; remove this optional event to use only passive hooks. |
| Uninstalled sidecar keeps restarting | Disable/remove the AI Agent Watchdog sidecar and hook entries in Antigravity. |

Useful commands from the repository:

```powershell
.\.venv\Scripts\python.exe -m agent_sentinel --config config/sentinel.json validate
.\scripts\status.ps1
Get-Content .sentinel\sentinel.log -Tail 20
```

`check` performs a single inspection and exits successfully if the engine ran, even
when provider status is unavailable. Use logs/status to assess integration health.
CLI errors deliberately omit exception details, command output and local paths.

When reporting issues, include OS, Python/AI Agent Watchdog/Antigravity versions, sanitized
timing configuration and event counts. Do not attach snapshots, generated integration
files, transcripts, routing IDs, credentials or full local paths. Automated integration
tests validate a fake CLI; live delivery and permissions need an environment smoke test.
