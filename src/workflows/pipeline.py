"""辯論流程建構模組

此模組提供 `build_pipeline` 函式，建立以 `Moderator` 為核心的辯論系統。
"""

from __future__ import annotations

from ..agents.advocate import Advocate
from ..agents.skeptic import Skeptic
from ..agents.moderator import Moderator


def build_pipeline() -> Moderator:
    """建立辯論流程

    回傳:
        Moderator: 已配置正反雙方代理的主持人。
    """
    advocate = Advocate(name="advocate", model="gemini-1.5-flash")
    skeptic = Skeptic(name="skeptic", model="gemini-1.5-flash")
    moderator = Moderator(
        name="moderator", model="gemini-1.5-flash", advocate=advocate, skeptic=skeptic
    )
    return moderator


if __name__ == "__main__":
    pipeline = build_pipeline()
    initial_state = {"proposal": "推廣太陽能發電"}
    final_state = pipeline.run(initial_state)
    for entry in final_state["log"]:
        print(f"{entry['speaker']}：{entry['message']}")
