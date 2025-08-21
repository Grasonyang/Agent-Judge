from __future__ import annotations

from src.workflows.moderator import Moderator


class _RepeatAgent:
    """總是回傳相同字串的假代理"""

    def __init__(self) -> None:
        self.name = "repeat"
        self.prompts: list[str] = []

    def chat(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "相同回覆"


def test_moderator_detects_repetition() -> None:
    agent = _RepeatAgent()
    mod = Moderator([agent], max_rounds=3, max_repeats=2)
    history = mod.run("問題？")

    assert history["repeat"] == ["相同回覆", "相同回覆"]
    assert agent.prompts[2] == "請換個角度回答：問題？"
    assert len(agent.prompts) == 3
