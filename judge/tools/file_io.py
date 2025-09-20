from __future__ import annotations
from pathlib import Path
import json
from typing import Any


def ensure_parent_dir(path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)


def write_json_file(path: str, data: Any) -> None:
    ensure_parent_dir(path)
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

