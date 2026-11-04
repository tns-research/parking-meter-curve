"""Append-only JSONL storage. Records are never rewritten; a trial counts as
done once a non-error record with its id exists."""

import json
import threading
from pathlib import Path

_lock = threading.Lock()


def read(path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def done_ids(path, id_field: str = "trial_id") -> set[str]:
    return {r[id_field] for r in read(path) if not r.get("is_error")}


def append(path, record: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with _lock, p.open("a") as f:
        f.write(line + "\n")
