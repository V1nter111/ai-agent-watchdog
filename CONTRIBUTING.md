# Contributing

Open an issue for a bug or provider proposal. Include reproducible, sanitized steps;
never publish real conversation snapshots, transcripts, tokens or local user paths.

Use Python 3.10+ and an isolated environment:

```sh
python -m venv .venv
# Use .venv/Scripts/python.exe on Windows, .venv/bin/python on Linux/macOS.
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
python -m build
```

The commands after venv creation assume it has been activated. Prefer deterministic
fake providers and subprocesses in tests; do not depend on personal Antigravity data.
Cover safety behavior when changing detection/recovery: completed jobs, live jobs,
cooldown, persisted limits, ambiguous delivery, invalid snapshots and state races.

New providers implement `Provider` in `providers/base.py`, normalize state into
`ConversationState`, and raise sanitized `ProviderError` failures. Add explicit config
validation/selection and fixtures. Keep engine policy independent of provider internals.
Do not add shell execution of untrusted snapshot fields, process termination or default
automatic destructive recovery. Preserve third-party permission decisions.

Before opening a PR, run tests/lint/build, review your diff for secrets and personal
data, update relevant docs and add a changelog entry. Describe the concrete behavior
and validation. Contributions are licensed under the project's existing MIT LICENSE.
