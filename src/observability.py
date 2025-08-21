"""整合外部觀測平台的事件回呼"""

from __future__ import annotations

import logging
from typing import Any, Callable

_WEAVE_ENABLED: bool | None = None
_weave = None


def _ensure_weave_initialized() -> None:
    """延遲初始化 Weave 平台"""
    global _WEAVE_ENABLED, _weave
    if _WEAVE_ENABLED is not None:
        return
    try:
        import weave  # type: ignore

        weave.init(project="agent-judge")
        _weave = weave
        _WEAVE_ENABLED = True
    except ImportError as exc:  # Weave 套件不存在
        logging.warning("無法載入 Weave：%s", exc)
        _WEAVE_ENABLED = False
    except weave.WeaveError as exc:  # 初始化失敗
        logging.warning("Weave 初始化失敗：%s", exc)
        _WEAVE_ENABLED = False


def _log(event: dict[str, Any]) -> None:
    """將事件送至 Weave，若無法使用則忽略"""
    _ensure_weave_initialized()
    if _WEAVE_ENABLED:
        _weave.log(event)  # type: ignore[union-attr]


def create_tool_callbacks(
    log_store: list[dict[str, Any]]
) -> tuple[Callable[..., Any], Callable[..., Any]]:
    """建立工具呼叫前後的回呼函式並記錄事件"""

    def _before_tool(tool, args, tool_context):  # type: ignore[no-untyped-def]
        log_store.append({"name": tool.name, "input": args})
        _log({"event": "before_tool", "tool": tool.name, "args": args})
        return None

    def _after_tool(tool, args, tool_context, result):  # type: ignore[no-untyped-def]
        if log_store:
            log_store[-1]["output"] = result
        _log(
            {
                "event": "after_tool",
                "tool": tool.name,
                "args": args,
                "result": result,
            }
        )
        return None

    return _before_tool, _after_tool

