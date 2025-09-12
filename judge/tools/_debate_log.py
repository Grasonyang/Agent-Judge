from __future__ import annotations
from typing import List, Optional
from pathlib import Path
import json
from pydantic import BaseModel,Field

from .evidence import Evidence
from ._record_utils import read_json_file, write_json_file


class Turn(BaseModel):
    """單一辯論回合資料模型"""
    speaker: str  # 發言者角色，如 advocate/skeptic/devil
    content: str  # 該回合的文字內容
    claim: Optional[str] = None  # 本回合提出或反駁的核心主張
    confidence: Optional[float] = None  # 發言者對主張的信心值
    evidence: List[Evidence] = Field(default_factory=list)# 使用到的證據列表
    fallacies: List[dict]     = Field(default_factory=list)  


def load_debate_log(path: str) -> List[Turn]:
    """讀取辯論紀錄檔（JSON array），若不存在則回傳空列表"""
    data = read_json_file(path, default=[])
    return [Turn.model_validate(item) for item in data]


def save_debate_log(path: str, turns: List[Turn]) -> None:
    """將所有回合寫入辯論紀錄檔（覆寫）。"""
    write_json_file(path, [t.model_dump() for t in turns])


def append_turn(path: str, turn: Turn) -> None:
    """附加單一回合到辯論紀錄檔"""
    turns = load_debate_log(path)
    turns.append(turn)
    save_debate_log(path, turns)


def initialize_debate_log(path: str, state: dict, reset: bool = True) -> None:
    """初始化辯論紀錄檔

    Args:
        path: 紀錄檔路徑
        state: 全域狀態，會寫入初始指標
        reset: 是否清空舊紀錄
    """
    p = Path(path)
    if reset and p.exists():
        p.unlink()
    turns = load_debate_log(path) if p.exists() else []
    state["debate_log_path"] = path
    # 初始化前次指標，供後續 Δ 計算
    claims = {t.claim for t in turns if t.claim}
    confidences = [t.confidence for t in turns if t.confidence is not None]
    evidences = [ev for t in turns for ev in t.evidence]
    state["prev_dispute_points"] = len(claims)
    state["prev_credibility"] = sum(confidences) / len(confidences) if confidences else 0.0
    state["prev_evidence_count"] = len(evidences)
    # 同步目前指標
    state["dispute_points"] = state["prev_dispute_points"]
    state["credibility"] = state["prev_credibility"]
    state["evidence"] = evidences
