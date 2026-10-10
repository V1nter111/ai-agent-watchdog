# AI Agent Watchdog: Google Antigravity 2.x

AI Agent Watchdog uses the documented [lifecycle hooks](https://antigravity.google/docs/hooks)
and [sidecar agentapi CLI](https://antigravity.google/docs/sidecars). Antigravity 2.19.1
on Windows passed a real automatic recovery test; see [validation](VALIDATION.md).
Other versions require their own smoke test. No stable public
snapshot listing API is assumed. Internal SQLite/protobuf stores are not read.

## Validated integration

The isolated Windows live test confirmed:

- Antigravity 2.19.1.
- Managed Sidecar integration.
- Real agentapi communication.
- Automatic stall detection and recovery message delivery.
- Agent continuation after recovery.
- Completion of the original process without restarting it.

The test used shorter timing thresholds than the defaults and a disposable project.
See [VALIDATION.md](VALIDATION.md) for timestamps and limits of this evidence.
Keep `dry_run: true` for normal setup until you validate your own environment.

## Generate the integration

After installation, run from the repository:

```powershell
.\.venv\Scripts\python.exe -m agent_sentinel --config config/sentinel.json integration
```

Files are generated inside the configured runtime directory, `.sentinel` by default.
They contain local installation paths and must remain private. Regenerate them if you
move the installation or change its virtual environment.

Version 0.2.0 fixes Windows hook quote escaping: simple paths use forward slashes
without unnecessary quotes; paths with spaces or shell characters use an encoded
PowerShell command that preserves stdin JSON. POSIX commands use shell argument quoting.
No changes to Shell Integration, MCP or Antigravity binaries are required.

## Enable hooks

Merge the `agent-sentinel` entry from `.sentinel/hooks.json` into your workspace
`.agents/hooks.json`, or into your global `~/.gemini/config/hooks.json`. Preserve existing
hooks. Enable it in Antigravity Settings > Customizations > Hooks. Hook commands use
the installed venv Python and absolute config path so they work outside the repo.

Default hooks are passive:

| Event | Recorded state |
| --- | --- |
| PreInvocation | Running; model invocation started |
| PostInvocation | Running; conservative tool grace because tool execution may follow |
| PostToolUse | Running; a tool step completed and progress advanced |
| Stop, fullyIdle=true | Completed; excluded from recovery |
| Stop, fullyIdle=false | Running with tool grace for active background work |

The collector stores only routing identity, event/time, progress and liveness flags.
It discards tool arguments, outputs, workspace/transcript paths, model metadata and
errors. It returns `{}` for invocation/post-tool events and `{"decision":"stop"}`
for Stop, without forcing continuation.

Optional: register the same collector with `--event PreToolUse` using the documented
tool matcher wrapper if you need exact tool-start visibility. It returns
`{"decision":"ask"}`, which respects existing grants but may add approval prompts.
This event is intentionally absent from generated hooks. It marks `ask_question` and
`ask_permission` as waiting for the user. Passive hooks alone cannot always identify
human waits, background job liveness or permission waits; use an adapter when those
distinctions are required. Missing terminal events after a crash can leave old running
snapshots; expiration limits their lifetime.

## Enable the sidecar

Create `~/.gemini/config/sidecars/agent-sentinel/` and copy the generated
`.sentinel/sidecar.json` there as `sidecar.json`. Merge this entry into the existing
`~/.gemini/config/config.json` (preserve other settings):

```json
{
  "sidecars": {
    "agent-sentinel": {"enabled": true}
  }
}
```

Reload Antigravity if needed. Sidecars receive `agentapi` in PATH. No `projectId` is
needed because AI Agent Watchdog sends to existing conversations and never creates new ones.
Do not also start the standalone watchdog. The single-instance lock prevents duplicates,
but a second sidecar instance can still create noisy restart errors.

Run a disposable conversation with a harmless tool and inspect AI Agent Watchdog status/logs.
`checked` should become nonzero. Dry-run must remain on until your observations are
reliable. To enable messages, set `dry_run: false` and restart the sidecar. An external
`status` process may show `agentapi_available: false` when only the sidecar has the
injected PATH; `watchdog_provider` preserves the daemon's last assessment, while
`provider` shows the current shell's assessment and current snapshot counts.

On Windows, the bundled `agentapi.bat` invokes `language_server.exe agentapi`.
The provider recognizes that wrapper and invokes the same native executable directly
with argument arrays, preserving multiline messages and avoiding batch shell expansion.
Other batch wrappers are rejected. You can also set `provider.agentapi_command` to
`["<Antigravity installation>/resources/bin/language_server.exe", "agentapi"]` using
your actual local path. Keep that machine-specific configuration private. Ordinary
shells still need the Antigravity API environment for actual delivery.

Before an upgrade, back up Antigravity configuration, hooks, sidecars and private
Sentinel configuration. Stop or disable only the Sentinel sidecar, run the installer,
regenerate integration and merge its named entry while preserving other customizations.
Keep the previous watchdog files until the new installation passes a disposable test.
Re-enable the managed sidecar with `dry_run: true`; do not start a duplicate daemon.

## Check the connection

Run from the installation directory:

```powershell
.\scripts\status.ps1
```

Expect `running: true` after enabling the Sidecar. After a harmless tool completes
in a disposable conversation, the daemon's last check should report a nonzero
`checked` count and `watchdog_provider.ready: true`. Examine `.sentinel/sentinel.log`
for checks and dry-run `would_recover` events when a stall is suspected.

Before hook events arrive, `state_source_available: false` can be normal. An ordinary
shell may lack the Sidecar's injected API environment; its `provider` assessment
does not replace the running daemon's `watchdog_provider` assessment. Missing
`watchdog_provider` means no daemon assessment has been saved yet. See
[troubleshooting](TROUBLESHOOTING.md) if readiness remains false after a test event.

To stop automatic messages, restore `dry_run: true` and restart the Sidecar. To stop
the watchdog process, disable only the `agent-sentinel` Sidecar in Antigravity.
Preserve other Sidecars, hooks, MCP and Shell Integration.

## Snapshot contract

Trusted adapters may write one JSON file per conversation to `provider.state_directory`.
Use atomic replacement. Field meanings:

| Field | Meaning |
| --- | --- |
| schema_version | Integer 1 |
| conversation_id | Runtime routing ID; never place a real ID in public examples |
| status | running, blocked, idle, completed or waiting_for_user |
| observed_at | Unix seconds of observation |
| last_progress_at | Unix seconds of actual progress, at or before observed_at |
| progress_token | Stable while no progress occurs; changes when progress occurs |
| tool_running | Boolean; true selects the longer tool grace |
| process_alive | Boolean or null; true suppresses recovery |

Poll timestamps alone must not change `last_progress_at` or `progress_token`. A repeated
write/mtime is not progress. Only supply `process_alive: true` with reliable evidence
about the actual job. No credentials or command text belong in this contract.

The provider finds snapshots, validates timestamps, identifies running tool steps and
sends `[agentapi_command..., "send-message", runtime_id, recovery_prompt]` without a
shell, with a configurable timeout. Invalid/expired files and duplicate routing IDs
are excluded; invalid counts appear in provider status. Active states are checked
again immediately before sending. A remaining race with external state updates is
unavoidable; no process termination is attempted.

Files over 64 KiB and symlinks are rejected. Protect the runtime directory with your
OS account permissions: snapshots are trusted local input and routing IDs remain on
disk there. AI Agent Watchdog is not a boundary against another process running as your user.
