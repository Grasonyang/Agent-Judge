from __future__ import annotations

from typing import Any, Dict, Set

from google.adk import Agent
from pydantic import PrivateAttr

from .advocate import Advocate
from .skeptic import Skeptic


class Moderator(Agent):
    """辯論主持代理類別

    角色任務：
        組織正反雙方進行辯論，負責初始陳述與後續質詢互動。
    """

    _advocate: Advocate = PrivateAttr()
    _skeptic: Skeptic = PrivateAttr()

    def __init__(self, name: str, advocate: Advocate, skeptic: Skeptic, **kwargs: Any) -> None:
        super().__init__(name=name, **kwargs)
        self._advocate = advocate
        self._skeptic = skeptic

    def _log(self, state: Dict[str, Any], speaker: str, message: str, seen: Set[str]) -> None:
        """記錄對話並檢測重複內容"""
        if message in seen:
            state.setdefault("duplicates", []).append({"speaker": speaker, "message": message})
        else:
            seen.add(message)
        state.setdefault("log", []).append({"speaker": speaker, "message": message})

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """執行辯論流程

        參數:
            state (Dict[str, Any]): 需包含 `proposal` 的狀態字典。

        回傳:
            Dict[str, Any]: 更新後的狀態，包含 `log` 與 `duplicates`。
        """
        proposal = state.get("proposal", "")
        seen: Set[str] = set()

        # 正反方初次陳述
        pro_opening = self._advocate.run(proposal)
        self._log(state, self._advocate.name, pro_opening, seen)

        con_opening = self._skeptic.run(proposal)
        self._log(state, self._skeptic.name, con_opening, seen)

        turn = "advocate"
        for _ in range(3):
            if turn == "advocate":
                # 重申立場
                stance = self._advocate.run(proposal)
                self._log(state, self._advocate.name, stance, seen)
                # 對手質疑
                question = self._skeptic.run(stance)
                self._log(state, self._skeptic.name, question, seen)
                # 回答問題
                answer = self._advocate.run(question)
                self._log(state, self._advocate.name, answer, seen)
                turn = "skeptic"
            else:
                stance = self._skeptic.run(proposal)
                self._log(state, self._skeptic.name, stance, seen)
                question = self._advocate.run(stance)
                self._log(state, self._advocate.name, question, seen)
                answer = self._skeptic.run(question)
                self._log(state, self._skeptic.name, answer, seen)
                turn = "advocate"

        return state
