from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("GEMINI_API_KEY", "dummy")
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.agents.advocate import Advocate
from src.agents.skeptic import Skeptic
from src.agents.jury import Jury
from src.llm_client import LlmClient


class _DummyLlm(LlmClient):
    """回傳固定裁決的假 LLM"""

    def __init__(self) -> None:
        pass

    def generate(self, prompt: str) -> str:
        return '{"winner": "advocate", "reason": "倡議者提出更多證據"}'


def test_jury_verdict_format() -> None:
    """檢查陪審團輸出格式與辯論流程整合"""
    advocate = Advocate(name="adv")
    skeptic = Skeptic(name="ske")

    proposal = "開發新能源"
    adv_msg = advocate.run(proposal)
    ske_msg = skeptic.run(adv_msg)

    transcript = [("Advocate", adv_msg), ("Skeptic", ske_msg)]
    positions = {"Advocate": adv_msg, "Skeptic": ske_msg}

    jury = Jury(name="jury", llm_client=_DummyLlm())
    verdict = jury.run(transcript, positions)

    assert verdict == {"winner": "advocate", "reason": "倡議者提出更多證據"}
