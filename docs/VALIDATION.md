# Validated integration: Antigravity 2.19.1

**PASS** — Windows, Python 3.12, Google Antigravity 2.19.1, 2026-10-10.

This live validation used the Agent Sentinel engine with local Windows integration
fixes that are now included in AI Agent Watchdog v0.2.0-alpha. The full release is also
covered by deterministic regression tests. No other Antigravity version is claimed
as validated.

## What passed

- Antigravity managed the Sidecar lifecycle and provided its agentapi environment.
- Passive lifecycle hooks discovered a real active task.
- A real 100-second silent PowerShell process produced an unchanged progress episode.
- The running watchdog automatically detected suspicion after repeated checks.
- It sent exactly one recovery message through the real agentapi CLI.
- The agent ran a continuation command successfully and acknowledged recovery.
- The original process completed without being killed or restarted.
- Cooldown suppressed subsequent recovery attempts.
- Backups were retained; normal settings and `dry_run: true` were restored.

The test ran in a dedicated empty Antigravity project. Only its real hook snapshot was
mirrored into a temporary isolated provider state directory, without changing timestamps
or progress tokens. The engine, provider interfaces and detection policy were unchanged.
The test controller created the conversation but never sent a recovery message itself.

## Test settings and evidence

| Setting | Temporary test value | Normal default |
| --- | --- | --- |
| interval_seconds | 5 | 120 |
| stale_seconds | 20 | 120 |
| tool_grace_seconds | 30 | 3600 |
| confirmation_checks | 2 | 2 |
| cooldown_seconds | 600 | 600 |
| max_recovery_attempts | 1 | 2 |
| dry_run | false | true |

All times below are UTC on 2026-10-10. No private paths, runtime identities, snapshots
or user transcript data are included in this public report.

| Event | Time |
| --- | --- |
| Test began | 15:54:25.941 |
| Silent process began | 15:54:32 |
| Detection check / persisted recovery reservation | 15:55:15.858 |
| Automatic recovery sent | 15:55:15.952 |
| Continuation command | 15:55:19 |
| Agent acknowledged recovery | 15:55:20 |
| Original process and test completed | 15:56:13 |
| Safe configuration restored | 15:56:18.480 |

The recovery cycle reported `checked=1`, `suspicious=1`, `recoveries=1`, `errors=0`.
The continuation command exited with code 0. In 0.1.0, detection time came from the
polling timestamp in the persisted reservation; 0.2.0 adds a distinct `stall_detected`
log event for future validations. A first attempt aborted on a Windows evidence-file
sharing violation before delivery; the successful retry produced the evidence above.

This proves automatic delivery and continuation at the temporary thresholds. A healthy
silent job can still look stalled: this test deliberately exercised that heuristic.
It does not prove a universal hang detector or detection of this 100-second job with
the normal one-hour tool grace. Configure grace and trusted process liveness for real
long-running jobs.

## Repeat safely

Back up configuration first. Use a separate empty Antigravity project and an isolated
state directory containing only that conversation's real hook state. Keep progress
timestamps unchanged, start a harmless silent background task and let the managed
watchdog perform repeated checks with temporary thresholds below the task duration.
Confirm `stall_detected`, `recovery_sent`, agent continuation and original task completion.
Do not send a recovery message manually as evidence of automatic recovery. Restore
normal thresholds and `dry_run: true` afterward; retain backups and sanitized evidence.
