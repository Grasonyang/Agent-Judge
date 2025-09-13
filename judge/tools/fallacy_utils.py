"""謬誤處理相關工具函式。"""

from __future__ import annotations
from typing import Any


def flatten_fallacies(messages: list) -> list:
    """將多則訊息中的謬誤扁平化為字典列表。

    Args:
        messages: 含有 `fallacies` 欄位的訊息列表。

    Returns:
        List[dict]: 扁平化後的謬誤清單，每項皆為字典。
    """
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
