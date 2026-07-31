import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

CONFIG_FILE = DATA_DIR / "config.json"
STATE_FILE = DATA_DIR / "count_state.json"
STAT_FILE = DATA_DIR / "stat_count.json"
DAILY_STATS_FILE = DATA_DIR / "daily_stats.json"


def _resolve_path(path: str | os.PathLike[str] | None) -> Path:
    if path is None:
        return CONFIG_FILE
    return Path(path)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=4)


def load_config(path: str | os.PathLike[str] | None = None):
    target = _resolve_path(path)
    if path is None:
        target = CONFIG_FILE

    if not target.exists():
        return {"counting_channel_id": 0}

    return _read_json(target)


def save_config(config: dict[str, Any], path: str | os.PathLike[str] | None = None) -> None:
    target = _resolve_path(path)
    if path is None:
        target = CONFIG_FILE

    _write_json(target, config)


def load_state(path: str | os.PathLike[str] | None = None):
    target = _resolve_path(path)
    if path is None:
        target = STATE_FILE

    if not target.exists():
        return {"last_number": 0, "last_user_id": None}

    return _read_json(target)


def save_state(state: dict[str, Any], path: str | os.PathLike[str] | None = None) -> None:
    target = _resolve_path(path)
    if path is None:
        target = STATE_FILE

    _write_json(target, state)


def load_stats(path: str | os.PathLike[str] | None = None):
    target = _resolve_path(path)
    if path is None:
        target = STAT_FILE

    if not target.exists():
        return {}

    return _read_json(target)


def save_stats(stats: dict[str, Any], path: str | os.PathLike[str] | None = None) -> None:
    target = _resolve_path(path)
    if path is None:
        target = STAT_FILE

    _write_json(target, stats)


def load_daily_stats(path: str | os.PathLike[str] | None = None):
    target = _resolve_path(path)
    if path is None:
        target = DAILY_STATS_FILE

    if not target.exists():
        return {}

    return _read_json(target)


def save_daily_stats(daily_stats: dict[str, Any], path: str | os.PathLike[str] | None = None) -> None:
    target = _resolve_path(path)
    if path is None:
        target = DAILY_STATS_FILE

    _write_json(target, daily_stats)
