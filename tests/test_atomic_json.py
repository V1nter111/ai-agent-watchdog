import json

import pytest

from agent_sentinel import logger


def test_windows_sharing_violation_retries_without_partial_state(tmp_path, monkeypatch):
    path = tmp_path / "status.json"
    logger.atomic_json(path, {"old": True})
    original = logger.os.replace
    calls = []
    def replace(source, target):
        calls.append(source)
        if len(calls) == 1:
            assert json.loads(path.read_text()) == {"old": True}
            error = PermissionError("sharing violation")
            error.winerror = 32
            raise error
        original(source, target)
    monkeypatch.setattr(logger, "_WINDOWS", True)
    monkeypatch.setattr(logger.os, "replace", replace)
    monkeypatch.setattr(logger.time, "sleep", lambda _: None)
    logger.atomic_json(path, {"new": True})
    assert len(calls) == 2
    assert json.loads(path.read_text()) == {"new": True}
    assert not list(tmp_path.glob(".tmp-*"))


def test_persistent_permission_failure_is_bounded_and_preserves_state(tmp_path, monkeypatch):
    path = tmp_path / "status.json"
    logger.atomic_json(path, {"old": True})
    calls = []
    def replace(*args):
        calls.append(args)
        error = PermissionError("access denied")
        error.winerror = 5
        raise error
    monkeypatch.setattr(logger, "_WINDOWS", True)
    monkeypatch.setattr(logger.os, "replace", replace)
    monkeypatch.setattr(logger.time, "sleep", lambda _: None)
    with pytest.raises(PermissionError):
        logger.atomic_json(path, {"new": True})
    assert len(calls) == 6
    assert json.loads(path.read_text()) == {"old": True}
    assert not list(tmp_path.glob(".tmp-*"))
