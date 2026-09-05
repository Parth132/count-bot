import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = ROOT / "data" / "deleted_messages.jsonl"
IST = ZoneInfo("Asia/Kolkata")


def _format_ist_timestamp(dt: datetime | None = None) -> str:
    current = dt or datetime.now(IST)
    return current.astimezone(IST).strftime("%d-%m-%Y %H:%M:%S IST")


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    return getattr(obj, key, default)


def log_deleted_message(
    message: Any,
    reason: str,
    deletion_source: str,
    bot_actor: dict[str, Any] | None = None,
    path: str | Path | None = None,
) -> None:
    try:
        target = Path(path) if path is not None else DEFAULT_LOG_PATH
        target.parent.mkdir(parents=True, exist_ok=True)

        author = _safe_get(message, "author", None)
        payload: dict[str, Any] = {
            "event": "message_deleted",
            "timestamp": _format_ist_timestamp(),
            "reason": reason,
            "deletion_source": deletion_source,
            "message": {
                "id": _safe_get(message, "id"),
                "content": _safe_get(message, "content", ""),
            },
            "author": {
                "id": _safe_get(author, "id"),
                "name": _safe_get(author, "name"),
                "display_name": _safe_get(author, "display_name"),
                "global_name": _safe_get(author, "global_name"),
            },
        }

        if bot_actor:
            payload["bot_actor"] = {
                "id": bot_actor.get("id"),
                "name": bot_actor.get("name"),
                "display_name": bot_actor.get("display_name"),
            }

        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

        prune_old_deleted_logs(target, retention_days=7)
    except Exception:
        # The bot must stay alive even if audit logging fails.
        return


def prune_old_deleted_logs(path: str | Path, retention_days: int = 7) -> None:
    target = Path(path)
    if not target.exists():
        return

    cutoff = datetime.now(IST) - timedelta(days=retention_days)
    valid_rows: list[str] = []

    with target.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            raw_timestamp = item.get("timestamp")
            if not raw_timestamp:
                valid_rows.append(line)
                continue

            try:
                dt = datetime.strptime(raw_timestamp, "%d-%m-%Y %H:%M:%S IST").replace(tzinfo=IST)
            except ValueError:
                valid_rows.append(line)
                continue

            if dt >= cutoff:
                valid_rows.append(line)

    with target.open("w", encoding="utf-8") as handle:
        for row in valid_rows:
            handle.write(row + "\n")
