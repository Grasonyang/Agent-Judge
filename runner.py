"""簡易 Runner，整合 LLM 回覆與工具結果"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agents.llm_agent import LlmAgent
from src.tools.search_news import search_news


@dataclass
class Runner:
    """執行代理並收斂工具與模型輸出"""

    agent: LlmAgent

    def run(self, query: str) -> dict[str, Any]:
        """執行單輪查詢並回傳整合結果"""
        # 呼叫工具搜尋新聞
        news = search_news(query)
        self.agent.tool_logs.append({
            "name": "search_news",
            "input": {"keyword": query},
            "output": news,
        })

        # 生成式模型回覆
        answer = self.agent.chat(f"請根據以下新聞提供摘要：{news}")
        return {"reply": answer, "tools": self.agent.tool_logs}


if __name__ == "__main__":
    runner = Runner(LlmAgent(name="demo"))
    result = runner.run("AI")
    print(result)
