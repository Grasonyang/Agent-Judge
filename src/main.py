from __future__ import annotations

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from .agents.advocate import Advocate
from .agents.jury import Jury
from .agents.skeptic import Skeptic
from .moderator import Debate, Moderator


def run_debate():
    """設定並執行一場完整的辯論。"""
    # 使用 gemini-pro 作為所有代理的模型
    # 使用 gemini-pro 作為所有代理的模型
    advocate = Advocate(name="Advocate", model="gemini-2.0-flash-exp")
    skeptic = Skeptic(name="Skeptic", model="gemini-2.0-flash-exp")
    jury = Jury(name="Jury", model="gemini-2.0-flash-exp")
    moderator = Moderator(name="Moderator", model="gemini-2.0-flash-exp")

    # 建立辯論流程
    debate = Debate(
        advocate=advocate, skeptic=skeptic, jury=jury, moderator=moderator, max_turns=2
    )

    # 執行辯論
    proposal = "所有國家的教育體系都應該將人工智慧倫理納入核心課程。"
    debate.run(proposal)


if __name__ == "__main__":
    run_debate()