# AI Agent Watchdog configuration

Copy `config/sentinel.example.json` to the gitignored `config/sentinel.json`. JSON with
an optional UTF-8 BOM is accepted. Unknown fields, wrong types, nonfinite numbers and
unsupported providers fail validation. Configuration is read once; restart after edits.

| Field | Default | Effect |
| --- | --- | --- |
| enabled | true | false disables checks and recovery |
| interval_seconds | 120 | Delay between checks after each check completes |
| stale_seconds | 120 | No-progress threshold and minimum local observation window |
| cooldown_seconds | 600 | Minimum time between reservations per conversation |
| max_recovery_attempts | 2 | Limit per unchanged progress episode; 0 disables recovery |
| confirmation_checks | 2 | Consecutive stale observations required |
| tool_grace_seconds | 3600 | Longer no-progress threshold while a tool may be running |
| dry_run | true | Log would_recover without sending or consuming attempts |
| runtime_directory | ../.sentinel | Lock, status, recovery ledger and rotating logs |
| provider.name | antigravity | Provider selection; only Antigravity in this release |
| provider.state_directory | ../.sentinel/conversations | Trusted JSON snapshots |
| provider.agentapi_command | ["agentapi"] | Executable and optional fixed arguments, never a shell command |
| provider.command_timeout_seconds | 30 | Maximum duration per send |
| provider.max_state_age_seconds | 86400 | Drop observations older than this |

Paths are relative to the **configuration file**, not the shell's working directory.
Use a private absolute path in your local config when needed. Never commit it.
Intervals and thresholds must be positive, except cooldown/tool grace may be zero.
Attempt limits are nonnegative integers; confirmation is a positive integer.
State age must exceed both stale and tool grace thresholds.

A fresh detector first observes a conversation; it waits at least `stale_seconds`
locally even if the snapshot is already old. It then requires `confirmation_checks`
consecutive stale checks. With defaults, a running state observed at t=0 can first
qualify at t=240. A tool first qualifies no earlier than t=3720 if its last progress
was t=0. Progress or known liveness resets confirmation. Missing states reset local
observation, but do not erase persisted recovery reservations.

Cooldown persists across progress changes. Attempts reset for a new progress token
or progress timestamp, after cooldown. The ledger hashes routing IDs and progress
tokens, and writes a reservation **before** sending. A timeout may mean the message
was delivered: it still consumes an attempt. Restarting preserves limits. Malformed
ledgers stop startup rather than permitting unlimited recovery. Do not delete the ledger
to bypass limits while the watchdog is active.

Long jobs should use a suitable tool grace or a trusted liveness/heartbeat adapter.
Hooks do not see CPU load, terminal output or every background process transition.
Elapsed time indicates suspicion, not proof. The recovery prompt asks the agent to
check the current operation rather than restart it.

`status` reports an OS lock as the current watchdog status; historical last-check
data survives shutdown. The live CLI configuration projection excludes private paths
and executable arguments. Logs rotate at 1 MB with three backups.
