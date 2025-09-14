"""主持人相關工具：提供退出迴圈與統計指標"""

from typing import Any
from pydantic import BaseModel
from google.adk.tools.agent_tool import AgentTool

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from .debaters.advocate.agent import advocate_agent
from .debaters.skeptic.agent import skeptic_agent
from .debaters.devil.agent import devil_agent
from .debaters.advocate import advocate_agent
from .debaters.skeptic import skeptic_agent
from .debaters.devil import devil_agent

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
    return None


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

        st["debate_messages"].append({
            "speaker": speaker,
            "content": payload,
            "claim": claim,
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
