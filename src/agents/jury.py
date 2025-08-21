from __future__ import annotations

import json
from typing import Dict, List, Tuple

from google.adk import Agent

from ..llm_client import LlmClient


class Jury(Agent):
    """陪審團代理

    角色任務：
        接收完整對話紀錄與雙方最終立場，透過 LLM 分析辯論強弱並給出裁決。

    輸入資料格式：
        `transcript` (`list[tuple[str, str]]`): 對話紀錄，元素為 `(角色, 發言)`。
        `positions` (`dict[str, str]`): 各方最終立場。

    輸出資料格式：
        `dict[str, str]`: 形如 `{"winner": "advocate", "reason": "理由"}` 的裁決。
    """

    def __init__(self, *args, llm_client: LlmClient | None = None, **kwargs) -> None:
        """建立陪審團代理並初始化 LLM 客戶端"""
        super().__init__(*args, **kwargs)
        # 若未提供客製 LLM，使用預設 LlmClient
        self._llm = llm_client or LlmClient()

    def run(self, transcript: List[Tuple[str, str]], positions: Dict[str, str]) -> Dict[str, str]:
        """執行陪審團裁決流程"""
        # 組裝提示文字供 LLM 分析
        parts = ["請評估以下辯論並以 JSON 格式回答勝方與理由。", "\n對話紀錄:"]
        for speaker, message in transcript:
            parts.append(f"{speaker}: {message}")
        parts.append("\n最終立場:")
        for side, stance in positions.items():
            parts.append(f"{side}: {stance}")
        parts.append('\n請輸出格式為 {"winner": "", "reason": ""}')
        prompt = "\n".join(parts)

        # 透過 LLM 產生判決
        response = self._llm.generate(prompt)
        try:
            verdict = json.loads(response)
        except Exception:
            # 若無法解析 JSON，將完整回應放入 reason
            verdict = {"winner": "unknown", "reason": response}
        return verdict
