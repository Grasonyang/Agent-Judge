"""主持人相關工具：提供退出迴圈與統計指標"""

from typing import Any
from pydantic import BaseModel
from google.adk.tools.agent_tool import AgentTool

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from .advocate import advocate_agent
from .skeptic import skeptic_agent
from .devil import devil_agent

LOG_MAP = {
    "call_advocate": ("advocate", "advocacy"),
    "call_skeptic": ("skeptic", "skepticism"),
    "call_devil": ("devil", "devil_turn"),
}


def exit_loop(tool_context):
    try:
        tool_context.actions.escalate = True
    except Exception:
        pass
    return {"ok": True}


def update_metrics(state):
    prev_points = state.get("prev_dispute_points", 0)
    curr_points = state.get("dispute_points", 0)
    state["delta_dispute_points"] = curr_points - prev_points
    state["prev_dispute_points"] = curr_points

    prev_cred = state.get("prev_credibility", 0.0)
    curr_cred = state.get("credibility", 0.0)
    state["delta_credibility"] = curr_cred - prev_cred
    state["prev_credibility"] = curr_cred

    prev_ev = state.get("prev_evidence_count", 0)
    curr_ev = len(state.get("evidence", []))
    state["new_evidence_gain"] = curr_ev - prev_ev
    state["prev_evidence_count"] = curr_ev


def should_stop(state) -> bool:
    return (
        state.get("delta_dispute_points", 0) <= 0
        or state.get("delta_credibility", 0) <= 0
        or state.get("new_evidence_gain", 0) <= 0
    )


def ensure_debate_messages(callback_context=None, **_):
    if callback_context is None:
        return None
    st = callback_context.state
    if "debate_messages" not in st or not isinstance(st.get("debate_messages"), list):
        st["debate_messages"] = []
    return None


def _summarize_payload(payload, speaker: str) -> str:
    try:
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump()
    except Exception:
        pass

    if isinstance(payload, dict):
        if speaker == "advocate":
            thesis = payload.get("thesis")
            points = payload.get("key_points") or []
            if thesis and isinstance(points, list):
                pts = "\n".join(f"- {p}" for p in points[:5])
                return f"Thesis: {thesis}\n{pts}".strip()
        if speaker == "skeptic":
            ct = payload.get("counter_thesis")
            ch = payload.get("challenges") or []
            if ct and isinstance(ch, list):
                pts = "\n".join(f"- {p}" for p in ch[:5])
                return f"Counter-thesis: {ct}\n{pts}".strip()
        if speaker == "devil":
            stance = payload.get("stance")
            atk = payload.get("attack_points") or []
            if stance and isinstance(atk, list):
                pts = "\n".join(f"- {p}" for p in atk[:5])
                return f"Stance: {stance}\n{pts}".strip()
    # fallback to string
    return str(payload)


async def log_tool_output(tool, args=None, tool_context=None, tool_response=None, result=None, append_event=None, **_):
    response = tool_response if tool_response is not None else result
    info = LOG_MAP.get(tool.name)
    if info:
        speaker, key = info
        st = tool_context.state if tool_context is not None else {}
        output = st.get(key)

        def _get(obj, k, default=None):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(k, default)
            return getattr(obj, k, default)
        claim = _get(output, "thesis") or _get(output, "counter_thesis") or _get(output, "stance")
        if hasattr(output, "model_dump"):
            payload = output.model_dump()
        elif isinstance(output, dict):
            payload = output
        else:
            payload = {"text": str(output)}

        # Create a human-friendly summary for content
        content_text = _summarize_payload(payload, speaker)

        st["debate_messages"].append({
            "speaker": speaker,
            "content": content_text,
            "claim": claim,
            "data": payload,
        })
        if append_event is not None:
            try:
                await append_event(
                    Event(
                        author=speaker,
                        actions=EventActions(
                            state_delta={
                                key: payload,
                                "debate_messages": st.get("debate_messages"),
                            }
                        ),
                    )
                )
            except Exception:
                pass
    return response


advocate_tool = AgentTool(advocate_agent)
advocate_tool.name = "call_advocate"
skeptic_tool = AgentTool(skeptic_agent)
skeptic_tool.name = "call_skeptic"
devil_tool = AgentTool(devil_agent)
devil_tool.name = "call_devil"


class NextTurnDecision(BaseModel):
    next_speaker: str
    rationale: str
