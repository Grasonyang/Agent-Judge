from __future__ import annotations
from typing import List, Optional
import json
from pydantic import BaseModel, Field

from google.adk.sessions.session import Session

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


def append_turn(state: dict, turn: Turn) -> None:
    """附加單一回合並即時更新指標。"""
    turns: List[Turn] = state.setdefault("debate_log", [])
    turns.append(turn)

    claims = {t.claim for t in turns if t.claim}
    confidences = [t.confidence for t in turns if t.confidence is not None]
    evidences = [ev for t in turns for ev in t.evidence]

    state["dispute_points"] = len(claims)
    state["credibility"] = sum(confidences) / len(confidences) if confidences else 0.0
    state["evidence"] = evidences


def initialize_debate_log(path: str, state: dict, reset: bool = True) -> None:
    """初始化辯論紀錄

    Args:
        path: 仍保留參數以維持介面相容
        state: 全域狀態
        reset: 是否重設現有紀錄
    """
    state["debate_log_path"] = path
    if reset:
        state["debate_log"] = []
        state["dispute_points"] = 0
        state["credibility"] = 0.0
        state["evidence"] = []
        state["prev_dispute_points"] = 0
        state["prev_credibility"] = 0.0
        state["prev_evidence_count"] = 0


def _turns_from_session(session: Session) -> List[Turn]:
    """從 Session 事件歷史擷取所有回合"""
    turns: List[Turn] = []
    seen = 0
    for ev in session.events:
        actions = getattr(ev, "actions", None)
        if not actions or not getattr(actions, "state_delta", None):
            continue
        state_delta = actions.state_delta
        msgs = state_delta.get("debate_messages")
        if not isinstance(msgs, list):
            continue
        while seen < len(msgs):
            msg = msgs[seen]
            speaker = msg.get("speaker") or ev.author
            content = msg.get("content")
            if isinstance(content, (dict, list)):
                content = json.dumps(content, ensure_ascii=False)
            # 取出 state_delta 中第一個非辯論訊息的 payload 以取得信心與證據
            payload = next((v for k, v in state_delta.items() if k != "debate_messages"), {})
            confidence = payload.get("confidence") if isinstance(payload, dict) else None
            evidence = payload.get("evidence", []) if isinstance(payload, dict) else []
            turn = Turn(
                speaker=speaker,
                content=content or "",
                claim=msg.get("claim"),
                confidence=confidence,
                evidence=evidence,
                fallacies=msg.get("fallacies", []),
            )
            turns.append(turn)
            seen += 1
    return turns


def update_state_from_session(state: dict, session: Session) -> None:
    """重新計算指標並寫回 state"""
    turns = _turns_from_session(session)
    state["debate_log"] = turns

    claims = {t.claim for t in turns if t.claim}
    confidences = [t.confidence for t in turns if t.confidence is not None]
    evidences = [ev for t in turns for ev in t.evidence]

    state["dispute_points"] = len(claims)
    state["credibility"] = sum(confidences) / len(confidences) if confidences else 0.0
    state["evidence"] = evidences


def export_debate_log(session: Session) -> str:
    """將 Session 事件轉換為 Turn 陣列並輸出 JSON"""
    turns = _turns_from_session(session)
    data = [t.model_dump() for t in turns]
    return json.dumps(data, ensure_ascii=False)
