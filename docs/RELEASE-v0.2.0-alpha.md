# AI Agent Watchdog v0.2.0-alpha

Powered by Agent Sentinel engine. This is the next release of the existing Agent
Sentinel project; repository history, providers and watchdog architecture are retained.
The existing repository is renamed to `V1nter111/ai-agent-watchdog`; the old URL redirects.

## Changes

- Public rebrand to AI Agent Watchdog; internal package `agent_sentinel`, CLI
  `agent-sentinel` and integration IDs remain compatible.
- Windows hook commands fix escaped executable quotes and support complex paths.
- Antigravity's Windows agentapi wrapper resolves to native argv delivery.
- Atomic state writes retry transient Windows sharing violations with bounded retries.
- New `stall_detected` logs make detection/recovery timestamps easier to validate.

## Validated Integrations

**PASS: Google Antigravity 2.19.1 on Windows, Python 3.12.** Verified managed Sidecar,
real agentapi communication, automatic stall detection, automatic recovery delivery,
agent continuation and original process completion without restart. An isolated
100-second silent task used temporary 5-second polling, 20-second staleness and
30-second tool grace. One automatic recovery was delivered; cooldown suppressed repeats.
Safe defaults and `dry_run: true` were restored. See [validation details](VALIDATION.md).

## Upgrade

Back up Antigravity configuration, hooks, sidecars and private Sentinel settings.
Stop or disable the Sentinel sidecar before running `scripts/install.ps1`. Regenerate
integration, merge the named hook and sidecar entries while preserving other settings,
and re-enable only the managed Sidecar. Start with `dry_run: true`. Shell Integration,
MCP and Antigravity binaries do not need replacement.

## Limits

This remains a heuristic alpha. Other Antigravity versions need their own validation.
Silent healthy jobs can exceed grace; trusted liveness suppresses recovery. The live
test does not validate default one-hour tool grace against every real freeze. Codex,
Claude Code and Gemini CLI providers remain planned. No live messages are enabled by
default, and the engine never kills or restarts successful processes.
