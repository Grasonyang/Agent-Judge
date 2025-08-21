from __future__ import annotations

"""倡議者代理，負責提出正面論述"""

from typing import Iterable

from .llm_agent import LlmAgent


class Advocate(LlmAgent):
    """倡議者代理類別"""

    def __init__(self, *args, context: str = "", **kwargs) -> None:
        """初始化代理並接收主持者上下文"""
        super().__init__(*args, **kwargs)
        self._context = context

    @property
    def context(self) -> str:
        """取得目前上下文"""
        return self._context

    def _merge_history(self, history: Iterable[str] | str) -> str:
        """將對話紀錄統一為字串"""
        if isinstance(history, str):
            return history
        if not history:
            return ""
        if isinstance(history[0], dict):
            return "\n".join([f"{turn.get('speaker', '')}: {turn.get('message', '')}" for turn in history])
        return "\n".join(history)

    def _build_prompt(self, history: Iterable[str] | str, action: str, host_prompt: str | None) -> str:
        """根據動作與主持者提示組合完整提示"""
        if host_prompt is not None:
            self._context = host_prompt
        history_text = self._merge_history(history)
        return f"{self._context}\n{action}\n{history_text}"

    def state_argument(self, history: Iterable[str] | str, host_prompt: str | None = None) -> str:
        """針對提案提出正面論點"""
        prompt = self._build_prompt(history, "請提出支持提案的論述。", host_prompt)
        return self.chat(prompt)

    def question_opponent(self, history: Iterable[str] | str, host_prompt: str | None = None) -> str:
        """向對手提出質疑"""
        prompt = self._build_prompt(history, "請向對手提出問題。", host_prompt)
        return self.chat(prompt)

    def answer_question(self, history: Iterable[str] | str, host_prompt: str | None = None) -> str:
        """回答對方的提問"""
        prompt = self._build_prompt(history, "請回答對方的問題。", host_prompt)
        return self.chat(prompt)

    def run(self, history: Iterable[str] | str) -> str:
        """維持相容性的舊介面，等同於 state_argument"""
        return self.state_argument(history)
