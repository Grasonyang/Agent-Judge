"""主持人相關工具：提供退出迴圈與統計指標"""

# --- moderator agent helpers moved from agent.py ---
from typing import Dict, Any
import json
from pydantic import BaseModel
from google.adk.tools.agent_tool import AgentTool

from judge.tools import (
    Turn,
    append_turn,
    initialize_debate_log,
    load_debate_log,
    append_event,
)
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from judge.agents.advocate.agent import advocate_agent
from judge.agents.skeptic.agent import skeptic_agent
from judge.agents.devil.agent import devil_agent
# 辯論紀錄檔路徑
LOG_PATH = "debate_log.json"

# 工具名稱與辯論記錄欄位對應
LOG_MAP = {
    "call_advocate": ("advocate", "advocacy"),
    "call_skeptic": ("skeptic", "skepticism"),
    "call_devil": ("devil", "devil_turn"),
}


def exit_loop(tool_context):
    """Deterministic tool：告訴 LoopAgent 退出迴圈。

    被設為工具後，LLM 或 deterministic enforcer 可以呼叫它以觸發 loop 停止。
    """
    try:
        tool_context.actions.escalate = True
    except Exception:
        pass
    return {"ok": True}


def update_metrics(state):
    """更新並寫入爭點、可信度與證據的變化量（提取自原 loop.py）"""
    # 若提供辯論紀錄路徑，先載入並更新目前指標
    log_path = state.get("debate_log_path")
    if log_path:
        turns = load_debate_log(log_path)
        state["dispute_points"] = len({t.claim for t in turns if t.claim})
        confidences = [t.confidence for t in turns if t.confidence is not None]
        state["credibility"] = sum(confidences) / len(confidences) if confidences else 0.0
        state["evidence"] = [ev for t in turns for ev in t.evidence]

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
    """判斷變化量是否觸發門檻（提取自原 loop.py）"""
    return (
        state.get("delta_dispute_points", 0) <= 0
        or state.get("delta_credibility", 0) <= 0
        or state.get("new_evidence_gain", 0) <= 0
    )

def ensure_debate_messages(callback_context=None, **_):
    """前置處理：目前無需額外動作，保留以維持介面一致。"""
    return None

def log_turn(state: Dict[str, Any], speaker: str, output) -> None:
    """Append a Turn to the debate log based on an agent's output."""
    log_path = state.get("debate_log_path")
    if not log_path:
        initialize_debate_log(LOG_PATH, state, reset=True)
        log_path = state.get("debate_log_path")

    def _get(obj, key, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    claim = _get(output, "thesis") or _get(output, "counter_thesis") or _get(output, "stance")

    if hasattr(output, "model_dump_json"):
        content = output.model_dump_json(ensure_ascii=False)
    elif isinstance(output, dict):
        content = json.dumps(output, ensure_ascii=False)
    elif isinstance(output, str):
        content = output
    else:
        try:
            content = json.dumps(output, default=str, ensure_ascii=False)
        except Exception:
            content = str(output)

    last_fallacies = None
    msgs = state.get("debate_messages") or []
    if msgs:
        last = msgs[-1]
        last_fallacies = (last.get("fallacies") if isinstance(last, dict)
                        else getattr(last, "fallacies", None))

    turn = Turn(
        speaker=speaker,
        content=content,
        claim=claim,
        confidence=_get(output, "confidence"),
        evidence=_get(output, "evidence", []),
        fallacies=last_fallacies or [],
    )
    append_turn(log_path, turn)
    # NOTE: recording to state_record is handled by each agent's own callback

def log_tool_output(tool, args=None, tool_context=None, tool_response=None, result=None, **_):
    response = tool_response if tool_response is not None else result
    info = LOG_MAP.get(tool.name)
    if info:
        speaker, key = info
        st = tool_context.state if tool_context is not None else {}
        output = st.get(key)

        if output:
            log_turn(st, speaker, output)

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
        # also write to state_record and keep in-memory agent log
        sr_path = st.get("state_record_path")
        if sr_path:
            try:
                # 將工具輸出記錄為事件並更新 state
                append_event(
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

# 把子代理包成可被呼叫的工具（a2a / a3a）
advocate_tool = AgentTool(advocate_agent)
advocate_tool.name = "call_advocate"
skeptic_tool = AgentTool(skeptic_agent)
skeptic_tool.name = "call_skeptic"
devil_tool = AgentTool(devil_agent)
devil_tool.name = "call_devil"


class NextTurnDecision(BaseModel):
    next_speaker: str
    rationale: str



