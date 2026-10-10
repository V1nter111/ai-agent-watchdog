# Changelog

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
