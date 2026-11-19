"""Append-only guardrail log. Raw prompts are not written."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG = Path(__file__).resolve().parents[1] / "logs" / "guardrail.jsonl"


def log_decision(event: dict) -> None:
    path = Path(os.environ.get("FSW_LOG_PATH") or DEFAULT_LOG)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts": datetime.now(timezone.utc).isoformat(), **event}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    except OSError:
        return
