from __future__ import annotations
from typing import List
from pathlib import Path
import json
from pydantic import BaseModel


class Turn(BaseModel):
    """單一辯論回合資料模型"""
    speaker: str  # 發言者角色，如 advocate/skeptic/devil
    content: str  # 該回合的文字內容


def load_debate_log(path: str) -> List[Turn]:
    """讀取辯論紀錄檔，若不存在則回傳空列表"""
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [Turn.model_validate(item) for item in data]


def save_debate_log(path: str, turns: List[Turn]) -> None:
    """將所有回合寫入辯論紀錄檔"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump([t.model_dump() for t in turns], f, ensure_ascii=False, indent=2)


def append_turn(path: str, turn: Turn) -> None:
    """附加單一回合到辯論紀錄檔"""
    turns = load_debate_log(path)
    turns.append(turn)
    save_debate_log(path, turns)
