# root_agent/agents/moderator/fallacy.py
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from google.genai import types

class FallacyItem(BaseModel):
    label: str
    quote: str
    explanation: str
    severity: Literal["low", "medium", "high"] = "low"

class FallacyOutput(BaseModel):
    fallacies: List[FallacyItem] = Field(default_factory=list)

def _ensure_fallacy_inputs(callback_context=None, **_):
    if not callback_context:
        return None
    state = getattr(callback_context, "state", None)
    if not isinstance(state, dict):
        return None

    # 確保有 debate_messages（給後續 fallback 用）
    state.setdefault("debate_messages", [])

    # 若 orchestrator_exec 不存在，嘗試用最後一則訊息當作「最新發言」
    if not state.get("orchestrator_exec"):
        last = state["debate_messages"][-1] if state["debate_messages"] else None
        text = ""
        if isinstance(last, dict):
            text = last.get("content", "") or last.get("message", "")
        elif isinstance(last, str):
            text = last
        state["orchestrator_exec"] = text

    return None




def _attach_to_last_turn(callback_context, **_):
    st = callback_context.state or {}
    detected = st.get("detected_fallacies", {}) or {}
    falls = detected.get("fallacies", [])

    if not falls:
        return None  # 沒抓到就不動最後一則，避免覆蓋成空
    msgs = st.setdefault("debate_messages", [])

    # 若目前沒有訊息，嘗試用 orchestrator_exec 建立一則
    if not msgs:
        content = st.get("orchestrator_exec", "")
        speaker = (st.get("next_decision") or {}).get("next_speaker") or "unknown"
        if content:
            msgs.append({
                "speaker": speaker,
                "content": {"text": content},
                "claim": None,
            })

    # 若現在終於有了最後一則，就把 fallacies 附上
    if msgs:
        last = msgs[-1]
        if isinstance(last, dict):
            last["fallacies"] = falls
        else:
            try:
                setattr(last, "fallacies", falls)
            except Exception:
                pass
    return None


fallacy_agent = LlmAgent(
    name="fallacy_detector",
    model="gemini-2.5-flash",
    instruction=(
    "你是邏輯謬誤檢測器。僅檢視【最新一則發言】找出潛在謬誤。\n"
    "輸入優先順序：1) {orchestrator_exec}；若不可用，2) 取 state['debate_messages'] 最末一則的文字。\n"
    "輸出限制：最多 3 條，每條 quote ≤ 120 字、explanation ≤ 150 字；severity 取 low/medium/high。\n"
    "只輸出 JSON，符合 FallacyOutput schema，不要多餘文字或註解。"
    ),
    output_schema=FallacyOutput,
    output_key="detected_fallacies",
    before_agent_callback=_ensure_fallacy_inputs,   # ✅ 關鍵：先把缺的欄位補齊
    after_agent_callback=_attach_to_last_turn,
    # 顯式關閉 transfer（避免那行警告）
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0, max_output_tokens=1024
    ),
)
