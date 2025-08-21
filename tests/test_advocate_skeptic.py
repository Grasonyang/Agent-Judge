from __future__ import annotations

"""測試 Advocate 與 Skeptic 的對話功能"""

import os
import sys
from pathlib import Path

os.environ.setdefault("GEMINI_API_KEY", "dummy")
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.agents.advocate import Advocate
from src.agents.skeptic import Skeptic
from src.llm_client import LlmClient


class _EchoLlm(LlmClient):
    """回傳提示內容的假 LLM"""

    def __init__(self) -> None:  # pragma: no cover - 不需初始化
        pass

    def generate(self, prompt: str) -> str:  # pragma: no cover - 簡化回傳
        return prompt


def test_advocate_context_and_history() -> None:
    """驗證倡議者能更新上下文並使用對話紀錄"""
    llm = _EchoLlm()
    advocate = Advocate(name="adv", model="dummy", llm_client=llm, context="初始提示")
    first = advocate.state_argument(["提案 A"])
    assert "初始提示" in first
    second = advocate.state_argument("提案 B", host_prompt="新提示")
    assert "新提示" in second and second != first


def test_skeptic_methods() -> None:
    """驗證懷疑者的方法與上下文更新"""
    llm = _EchoLlm()
    skeptic = Skeptic(name="sk", model="dummy", llm_client=llm, context="背景")
    question = skeptic.question_opponent("主張")
    assert "背景" in question
    answer = skeptic.answer_question(["疑問"], host_prompt="更新背景")
    assert "更新背景" in answer and answer != question
