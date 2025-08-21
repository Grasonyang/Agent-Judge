from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.workflows.pipeline import build_pipeline


def test_moderator_debate_flow() -> None:
    """驗證主持人能夠管理完整辯論流程"""
    moderator = build_pipeline()
    state = {"proposal": "推廣太陽能發電"}
    result = moderator.run(state)

    assert "log" in result
    assert len(result["log"]) == 11
    assert "duplicates" in result
    assert len(result["duplicates"]) > 0
