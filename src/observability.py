"""整合外部觀測平台的事件回呼"""

from __future__ import annotations

from typing import Any, Callable

try:
    import weave  # type: ignore

    _WEAVE_ENABLED = True
    weave.init(project="agent-judge")
except Exception:  # pylint: disable=broad-except
    _WEAVE_ENABLED = False


def _log(event: dict[str, Any]) -> None:
    """將事件送至 Weave，若無法使用則忽略"""
    if _WEAVE_ENABLED:
        weave.log(event)


def create_tool_callbacks(log_store: list[dict[str, Any]]) -> tuple[Callable[..., Any], Callable[..., Any]]:
    """建立工具呼叫前後的回呼函式並記錄事件"""

    def _before_tool(tool, args, tool_context):  # type: ignore[no-untyped-def]
        log_store.append({"name": tool.name, "input": args})
        _log({"event": "before_tool", "tool": tool.name, "args": args})
        return None

    def _after_tool(tool, args, tool_context, result):  # type: ignore[no-untyped-def]
        if log_store:
            log_store[-1]["output"] = result
        _log({"event": "after_tool", "tool": tool.name, "args": args, "result": result})
        return None

    return _before_tool, _after_tool
