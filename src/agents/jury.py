from __future__ import annotations

from typing import Iterable

from .llm_agent import LlmAgent


class Jury(LlmAgent):
    """陪審團代理類別

    角色任務：
        根據完整的辯論歷史紀錄，進行分析並提供最終裁決。

    輸入資料格式：
        `history` (`Iterable[str]` | `str`): 辯論的完整歷史紀錄。

    輸出資料格式：
        `str`: 陪審團的最終裁決與分析。
    """

    def _build_prompt(self, history: Iterable[str] | str) -> str:
        """建立用於裁決的提示"""
        if isinstance(history, str):
            history_text = history
        else:
            history_text = "\n".join(history)

        return f"""
        作為一個公正的陪審團，請根據以下完整的辯論紀錄，分析雙方的論點、質詢和回答。
        你的任務是：
        1.  總結正方（advocate）和反方（skeptic）的核心論點。
        2.  評估誰的論點更有說服力，誰的回答更能應對質詢。
        3.  基於上述分析，給出你的最終裁決，並解釋理由。

        辯論紀錄：
        {history_text}

        請提供你的最終裁決與分析：
        """

    def run(self, history: Iterable[str] | str) -> str:
        """執行裁決流程

        參數:
            history (Iterable[str] | str): 辯論的完整歷史紀錄。

        回傳:
            str: 陪審團的最終裁決與分析。
        """
        prompt = self._build_prompt(history)
        return self.chat(prompt)