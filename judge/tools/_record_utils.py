from __future__ import annotations
from pathlib import Path
import json
from typing import Any, List, Optional


def ensure_parent_dir(path: str) -> None:
    """Ensure the parent directory of path exists."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)


def read_json_file(path: str, default: Optional[Any] = None) -> Any:
    """Read JSON file and return parsed value. Returns default when file missing."""
    p = Path(path)
    if not p.exists():
        return default if default is not None else []
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json_file(path: str, data: Any) -> None:
    """Write JSON data to path (creates parent dirs)."""
    ensure_parent_dir(path)
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_to_json_array(path: str, item: Any) -> None:
    """Read a JSON array from path (or []) and append an item, then write back."""
    arr = read_json_file(path, default=[])
    arr.append(item)
    write_json_file(path, arr)


def append_ndjson(path: str, obj: Any) -> None:
    """Append a single JSON object as one line (ndjson)."""
    ensure_parent_dir(path)
    p = Path(path)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_ndjson(path: str) -> List[dict]:
    """Read newline-delimited JSON file into list of dicts, skipping malformed lines."""
    p = Path(path)
    if not p.exists():
        return []
    records: List[dict] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                # tolerant: skip malformed line
                continue
    return records
