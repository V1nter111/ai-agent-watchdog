# AI Agent Watchdog changelog

## 0.2.0-alpha — 2026-10-10

- Rebrand the public project as AI Agent Watchdog, powered by Agent Sentinel engine.
  Update documentation, CLI help and sidecar display name. Distribution: `0.2.0a0`.
- Preserve package names, CLI commands, integration identifiers and watchdog behavior.
- Fix Windows hook quote escaping, with encoded PowerShell handling for complex paths.
- Recognize Antigravity's bundled Windows agentapi wrapper and use native argv delivery.
  Reject unrecognized batch wrappers rather than shell-expanding recovery content.
- Retry transient Windows file-sharing failures during atomic state replacement, with
  bounded retries that preserve the previous file on persistent failure.
- Add sanitized `stall_detected` evidence before recovery for timestamp validation.
- Document PASS on Antigravity 2.19.1: Sidecar integration, real agentapi, automatic
  detection/delivery, agent continuation and original process completion without restart.
  The isolated test used reduced timing thresholds; safe defaults were restored.
- Add regression tests for hook execution, wrapper argv safety, file-sharing retries
  and automatic detection/recovery evidence. Retain all existing tests and providers.

## 0.1.0-alpha — 2026-10-10

First public alpha preparation. Python distribution version: `0.1.0a0`.

- Provider-neutral watchdog with stale confirmation, tool grace, cooldown and limits.
- Antigravity 2.x snapshot provider, documented hook collector and agentapi recovery.
- Passive hook/sidecar configuration generator and dry-run defaults.
- Persistent recovery reservations, single-instance locking and structured rotating logs.
- Windows install/start/stop/status/uninstall scripts, configuration and troubleshooting guides.
- Detector, recovery, configuration, provider and engine regression tests; Windows/Linux CI.

Known limits: heuristic detection; no native database discovery; passive hooks cannot
prove process liveness or identify every user wait; live Antigravity delivery remains
to be verified. Codex, Claude Code and Gemini CLI providers are planned.
