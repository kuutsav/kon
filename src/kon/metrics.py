from __future__ import annotations

import json
from datetime import UTC, datetime

from kon.config import get_config_dir


def get_turn_metrics_path():
    return get_config_dir() / "turn-metrics.jsonl"


def append_run_metric(
    *,
    session_id: str | None,
    provider: str | None,
    model: str,
    turn_metrics: list[tuple[int, float]],
    tool_call_count: int,
    stop_reason: str,
) -> None:
    path = get_turn_metrics_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "session_id": session_id,
        "provider": provider,
        "model": model,
        "turn_metrics": [[output, round(seconds, 2)] for output, seconds in turn_metrics],
        "tool_call_count": tool_call_count,
        "stop_reason": stop_reason,
    }
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass
