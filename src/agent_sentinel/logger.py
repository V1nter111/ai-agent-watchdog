"""JSON lines logging and atomic private runtime state."""

import json
import logging
import os
import tempfile
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

_WINDOWS = os.name == "nt"


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, name = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, allow_nan=False)
        for attempt in range(6):
            try:
                os.replace(name, path)
                break
            except PermissionError as exc:
                if not _WINDOWS or getattr(exc, "winerror", None) not in {5, 32, 33} or attempt == 5:
                    raise
                time.sleep(0.05)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"time": time.time(), "level": record.levelname,
                           "event": record.getMessage(), **getattr(record, "data", {})})


def make_logger(runtime: Path) -> logging.Logger:
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    logger = logging.getLogger("agent_sentinel")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    for handler in (logging.StreamHandler(), RotatingFileHandler(
            runtime / "sentinel.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")):
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger
