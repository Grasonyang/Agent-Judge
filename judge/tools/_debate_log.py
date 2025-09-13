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


def recalculate_metrics(turns: List[Turn]) -> dict:
    """根據所有回合重新計算辯論指標

    - dispute_points：去除重複主張後的數量
    - credibility：所有回合信心值的平均，若無則為 0
    - evidence：彙整所有回合使用到的證據
    """
    claims = {t.claim for t in turns if t.claim}
    confidences = [t.confidence for t in turns if t.confidence is not None]
    evidences = [ev for t in turns for ev in t.evidence]
    return {
        "dispute_points": len(claims),
        "credibility": sum(confidences) / len(confidences) if confidences else 0.0,
        "evidence": evidences,
    }


def append_turn(state: dict, turn: Turn) -> None:
    """附加單一回合並即時更新指標。"""
    turns: List[Turn] = state.setdefault("debate_log", [])
    turns.append(turn)

    # 重新計算爭議點（主張數量）、可信度平均與證據彙整
    state.update(recalculate_metrics(turns))


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

    # 依回合重新計算爭議點（主張數量）、可信度平均與證據彙整
    state.update(recalculate_metrics(turns))


def export_debate_log(session: Session) -> str:
    """將 Session 事件轉換為 Turn 陣列並輸出 JSON"""
    turns = _turns_from_session(session)
    data = [t.model_dump() for t in turns]
    return json.dumps(data, ensure_ascii=False)


def export_session(session: Session) -> dict:
    """整理 Session state 與事件並回傳 dict"""

    # 依前綴分層 state：app、user、shared
    state_scoped = {"app": {}, "user": {}, "shared": {}}
    for key, value in session.state.items():
        if key.startswith("app:"):
            state_scoped["app"][key[4:]] = value
        elif key.startswith("user:"):
            state_scoped["user"][key[5:]] = value
        else:
            state_scoped["shared"][key] = value

    # 將事件完整輸出為 list[dict]
    events = [ev.model_dump() for ev in session.events]

    return {
        "session": {
            "id": session.id,
            "app_name": session.app_name,
            "user_id": session.user_id,
            "last_update_time": session.last_update_time,
        },
        "state": state_scoped,
        "events": events,
    }

