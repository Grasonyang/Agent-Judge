"""自訂 LLM 代理，於初始化時載入工具並紀錄事件"""

from __future__ import annotations

from typing import Any

from google.adk.agents.llm_agent import LlmAgent as AdkLlmAgent
from google.adk.tools import google_search
from pydantic import PrivateAttr

from ..llm_client import LlmClient
from ..tools.search_news import search_news
from ..observability import create_tool_callbacks


class LlmAgent(AdkLlmAgent):
    """整合多項工具的 LLM 代理"""

    _tool_logs: list[dict[str, Any]] = PrivateAttr(default_factory=list)
    _llm: LlmClient = PrivateAttr()

    def __init__(
        self,
        *args,
        llm_client: LlmClient | None = None,
        **kwargs,
    ) -> None:
        """初始化代理並註冊工具與回呼"""
        # 註冊預設工具
        tools = list(kwargs.pop("tools", []))
        tools.extend([google_search, search_news])
        kwargs["tools"] = tools

        super().__init__(*args, **kwargs)

        # 建立或使用傳入的 LLM 客戶端以支援多輪對話
        model = kwargs.get("model", "gemini-pro")
        self._llm = llm_client or LlmClient(model=model)

        before_tool, after_tool = create_tool_callbacks(self._tool_logs)
        self.before_tool_callback = before_tool
        self.after_tool_callback = after_tool

    @property
    def tool_logs(self) -> list[dict[str, Any]]:
        """取得工具執行紀錄"""
        return self._tool_logs

    def chat(self, message: str) -> str:
        """透過 LLM 客戶端產生回覆"""
        return self._llm.generate(message)
