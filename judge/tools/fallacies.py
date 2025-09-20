"""謬誤處理相關工具函式。"""

from __future__ import annotations
from typing import Any


def flatten_fallacies(messages: list) -> list:
    if not messages:
        return []
    flat: list[dict[str, Any]] = []
    for msg in messages:
        falls = msg.get("fallacies") if isinstance(msg, dict) else getattr(msg, "fallacies", None)
        if not falls:
            continue
        for f in falls:
            if hasattr(f, "model_dump"):
                flat.append(f.model_dump())
            else:
                flat.append(dict(f))
    return flat

