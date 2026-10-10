# AI Agent Watchdog

> Prevent AI coding agents from silently freezing during long-running tasks.

AI Agent Watchdog is an open-source watchdog for autonomous AI coding agents. Terminal
commands, builds, tests, Docker tasks, migrations and background jobs can stop making
progress while an agent continues to wait. AI Agent Watchdog periodically checks conversation
progress and sends a bounded, conservative recovery reminder when a stall is suspected.

The first provider targets **Google Antigravity 2.x**, using its documented hooks and
`agentapi send-message` command. Provider interfaces allow future Codex, Claude Code
and Gemini CLI integrations. This alpha is a heuristic watchdog, not a guarantee that
every freeze is detected or every long job is distinguished from a freeze.

AI Agent Watchdog is powered by the Agent Sentinel monitoring engine.
Current release: **v0.1.0-alpha**. The Python package (`agent_sentinel`), CLI command
(`agent-sentinel`) and integration identifiers retain their existing names.

## Features

- Configurable polling, stale thresholds and repeated confirmation.
- Extra grace for tool operations; explicit process liveness suppresses recovery.
- Cooldown and a persisted attempt limit per unchanged progress episode.
- Dry-run enabled by default; failed sends also consume an attempt.
- State revalidation before a send; idle, completed and human-wait states are excluded.
- JSON logs with rotation, hashed conversation references and no tool output.
- OS-managed single-instance lock; graceful shutdown; Windows lifecycle scripts.
- Python 3.10+, no third-party runtime dependencies. MIT licensed.

## Install on Windows

```powershell
git clone https://github.com/V1nter111/agent-sentinel.git
cd agent-sentinel
.\scripts\install.ps1
```

The installer checks Python, creates `.venv`, installs the package, creates the private
`config/sentinel.json` without overwriting existing settings, and validates CLI startup.
Use `install.ps1 -Dev` for pytest, Ruff and build tooling. If PowerShell blocks scripts,
review them and use a process-scoped execution policy appropriate for your environment.

On Linux/macOS:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
cp config/sentinel.example.json config/sentinel.json
.venv/bin/python -m agent_sentinel --config config/sentinel.json validate
```

## Connect Antigravity

```powershell
.\.venv\Scripts\python.exe -m agent_sentinel --config config/sentinel.json integration
```

This generates **private**, machine-specific `.sentinel/hooks.json` and
`.sentinel/sidecar.json`. Follow [the connection guide](docs/ANTIGRAVITY.md) to merge
the hook entry and enable the sidecar. Existing conversations become discoverable
after their next hook event. No manually hardcoded conversation IDs are needed.

Antigravity supplies `agentapi` to sidecars. A standalone Windows process must instead
have the Antigravity `agentapi` executable available through PATH or
`provider.agentapi_command`. Do not install a different product also named AgentAPI.

State collection uses documented hook payloads, not an undocumented database decoder.
The provider also accepts explicit normalized JSON snapshots from a trusted adapter.
See [the state contract](docs/ANTIGRAVITY.md#snapshot-contract). Live Antigravity
delivery must be verified in your environment; the automated suite uses a fake CLI.

## Run and inspect

For standalone operation:

```powershell
.\scripts\start.ps1
.\scripts\status.ps1
.\scripts\stop.ps1
```

For foreground operation or a single safe inspection:

```powershell
.\.venv\Scripts\python.exe -m agent_sentinel --config config/sentinel.json run
.\.venv\Scripts\python.exe -m agent_sentinel --config config/sentinel.json check
```

Do not run the sidecar and standalone watchdog at the same time. `status` reports the
OS lock, provider readiness, last check and effective timing configuration. JSON log
events are written to `.sentinel/sentinel.log`. `check` performs one inspection; repeated
confirmation requires the daemon or multiple checks in the same process, so separate
invocations of `check` do not send recovery messages.

Keep `dry_run: true` while validating your hook setup. When `checked` is nonzero and
`would_recover` events match real stalls, set `dry_run: false` and restart the watchdog.
Before enabling live messages, use a disposable conversation to test your `agentapi`
installation. AI Agent Watchdog does not kill processes or restart commands.

## Change the interval

Edit `config/sentinel.json`:

```json
{
  "interval_seconds": 120,
  "stale_seconds": 120,
  "cooldown_seconds": 600,
  "max_recovery_attempts": 2
}
```

These are fields to modify in the full config, not a replacement file. Restart after
editing. `tool_grace_seconds` defaults to 3600 for potentially long tool work.
[Configuration reference](docs/CONFIGURATION.md) explains thresholds and limitations.

## Recovery reminder

```text
ANTI_HANG_RECOVERY:

Check current task state.

If process is still running:
continue monitoring.

If completed:
continue original task.

If blocked:
diagnose and recover safely.

Do not restart successful operations.
Do not perform destructive actions.
```

The agent still decides how to proceed and retains its own permissions. The prompt
does not enforce agent behavior. A silent operation beyond the grace window can be
suspected; supply trusted liveness information or raise the grace for long jobs.

## Troubleshooting and uninstall

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for missing `agentapi`, no detected
conversations, runtime locks and malformed state. `scripts/uninstall.ps1` stops and
uninstalls the package while retaining configuration and runtime data. Remove any
Antigravity hook/sidecar entries you enabled before deleting the installation directory.

Private configuration and runtime files are gitignored. Snapshot files necessarily
contain local conversation routing IDs; never commit or publish them. Public source,
examples, logs and the recovery ledger contain no real conversation IDs or credentials.

## Development and roadmap

```powershell
.\scripts\install.ps1 -Dev
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m build
```

CI runs tests, lint and package builds on Windows/Linux with Python 3.10, 3.12 and 3.13.
See [CONTRIBUTING.md](CONTRIBUTING.md). Planned: live Antigravity compatibility fixtures,
process/heartbeat adapters, per-tool grace, notifications, and Codex/Claude Code/Gemini
CLI providers. See [CHANGELOG.md](CHANGELOG.md) for this release.

## Keywords

- AI agent watchdog
- coding agent reliability
- autonomous AI agents
- LLM agents
- agent recovery
- agent monitoring
