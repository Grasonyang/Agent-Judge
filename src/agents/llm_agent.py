"""自訂 LLM 代理，於初始化時載入工具並紀錄事件"""

from __future__ import annotations

from typing import Any

from google.adk.agents.llm_agent import LlmAgent as AdkLlmAgent
from google.adk.tools import google_search

from ..tools.search_news import search_news


class LlmAgent(AdkLlmAgent):
    """整合多項工具的 LLM 代理"""

    def __init__(self, *args, **kwargs) -> None:
        """初始化代理並註冊工具與回呼"""
        self.tool_logs: list[dict[str, Any]] = []

        tools = list(kwargs.pop("tools", []))
        tools.extend([google_search, search_news])
        kwargs["tools"] = tools

        def _before_tool(tool, args, tool_context):
            self.tool_logs.append({"name": tool.name, "input": args})
            return None

        def _after_tool(tool, args, tool_context, result):
            if self.tool_logs:
                self.tool_logs[-1]["output"] = result
            return None

        kwargs["before_tool_callback"] = _before_tool
        kwargs["after_tool_callback"] = _after_tool

        super().__init__(*args, **kwargs)
