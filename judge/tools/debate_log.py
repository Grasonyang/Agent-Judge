from __future__ import annotations
from typing import List, Optional
import json
from pydantic import BaseModel, Field

from google.adk.events.event import Event
from google.adk.sessions.session import Session

from .evidence import Evidence


class Turn(BaseModel):
    speaker: str
    content: str
    claim: Optional[str] = None
    confidence: Optional[float] = None
    evidence: List[Evidence] = Field(default_factory=list)
    fallacies: List[dict] = Field(default_factory=list)


def recalculate_metrics(turns: List[Turn]) -> dict:
    claims = {t.claim for t in turns if t.claim}
    confidences = [t.confidence for t in turns if t.confidence is not None]
    evidences = [ev for t in turns for ev in t.evidence]
    return {
        "dispute_points": len(claims),
        "credibility": sum(confidences) / len(confidences) if confidences else 0.0,
        "evidence": evidences,
    }


def append_turn(state: dict, turn: Turn) -> None:
    turns: List[Turn] = state.setdefault("debate_log", [])
    turns.append(turn)
    state.update(recalculate_metrics(turns))


def append_event_update(state: dict, event: Event) -> None:
    actions = getattr(event, "actions", None)
    if not actions or not getattr(actions, "state_delta", None):
        return
    state_delta = actions.state_delta
    msgs = state_delta.get("debate_messages")
    if not isinstance(msgs, list):
        return
    turns: List[Turn] = state.setdefault("debate_log", [])
    seen = len(turns)
    payload = next((v for k, v in state_delta.items() if k != "debate_messages"), {})
    for msg in msgs[seen:]:
        speaker = msg.get("speaker") or event.author
        content = msg.get("content")
        if isinstance(content, (dict, list)):
            content = json.dumps(content, ensure_ascii=False)
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
        append_turn(state, turn)


def initialize_debate_state(state: dict, reset: bool = True) -> None:
    if reset:
        state["debate_messages"] = []
        state["debate_log"] = []
        state["dispute_points"] = 0
        state["credibility"] = 0.0
        state["evidence"] = []
        state["prev_dispute_points"] = 0
        state["prev_credibility"] = 0.0
        state["prev_evidence_count"] = 0


def _turns_from_session(session: Session) -> List[Turn]:
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
    turns = _turns_from_session(session)
    state["debate_log"] = turns
    state.update(recalculate_metrics(turns))


def export_debate_log(session: Session) -> str:
    turns = _turns_from_session(session)
    data = [t.model_dump() for t in turns]
    return json.dumps(data, ensure_ascii=False)


def export_session(session: Session) -> dict:
    state_scoped = {"app": {}, "user": {}, "shared": {}}
    for key, value in session.state.items():
        if key.startswith("app:"):
            state_scoped["app"][key[4:]] = value
        elif key.startswith("user:"):
            state_scoped["user"][key[5:]] = value
        else:
            state_scoped["shared"][key] = value
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

