from typing import List
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent,SequentialAgent
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
import json
from google.genai import types
from judge.tools import flatten_fallacies
import re




class ScoreDetail(BaseModel):
    evidence_quality: int = Field(ge=0, le=30, description="證據品質 0~30")
    logical_rigor: int = Field(ge=0, le=30, description="邏輯嚴謹性 0~30")
    robustness: int = Field(ge=0, le=20, description="論證韌性 0~20")
    social_impact: int = Field(ge=0, le=20, description="社會影響力 0~20")
    total: int = Field(ge=0, le=100, description="四項加總")


class Finding(BaseModel):
    point: str
    refs: List[str] = Field(default_factory=list, description="可附上引用的URL清單")


class JuryOutput(BaseModel):
    verdict: str = Field(description="簡短結論：如 '正方較有說服力' 或 '證據不足'")
    verdict_result: str = Field(description="清楚說明哪一方比較強，回答'正方'或'反方'，回答這兩個的其中一個")
    strengths: List[Finding] = Field(description="哪一方強在哪裡（2~5 條）")
    weaknesses: List[Finding] = Field(description="主要缺陷或風險（2~5 條）")
    flagged_fallacies: List[str] = Field(default_factory=list, description="主持人或評審辨識的邏輯謬誤")
    next_questions: List[str] = Field(default_factory=list, description="尚待澄清/查證的重點問題")



def _ensure_and_flatten_fallacies(callback_context=None, **_):
    if callback_context is None:
        return None
    state = callback_context.state
    # 保底確保存在辯論訊息陣列，避免 KeyError
    msgs = state.get("debate_messages") or []
    state["debate_messages"] = msgs
    state["fallacy_list"] = flatten_fallacies(msgs)
    return None


jury_pretty_after = None

def _build_jury_after():
    def _after(agent_context=None, **_):
        if agent_context is None:
            return None
        st = agent_context.state
        out = st.get("jury_result")
        if out is None:
            return None
        try:
            if hasattr(out, "model_dump"):
                data = out.model_dump()
            else:
                data = out
            msg = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            msg = str(out)
        return Event(author="jury", actions=EventActions(message=msg))
    return _after

jury_pretty_after = _build_jury_after()

jury_agent = LlmAgent(
    name="jury",
    model="gemini-2.0-flash",
    instruction=(
        "你是陪審團，請根據完整辯論紀錄與證據，對文本的真實性進行客觀量化評分並給出裁決。\n\n"
        "裁決目標是判斷輸入文本的真實性，請勿脫離判斷真實性的目標。\n\n"
        "如果判斷文本有時間資訊，請以該時間資訊的時間點判斷哪一方勝利。\n\n"
        "【判斷文本】\n"
        "{_init_session}\n\n"
        "【辯論紀錄】\n"
        "- 反方初始論點：state['skepticism1']"
        "- 正方初始論點：state['advocacy1']"
        "- 正方質疑反方的論點：state['advocacy2']"
        "- 反方反駁：state['skepticism2']"
        "- 反方質疑正方的論點：state['skepticism3']"
        "- 正方反駁：state['advocacy3']"
        "- 正方最終論述：state['advocacy4']" \
        "- 反方最終論述：state['skepticism4']\n\n"
        "【證據】\n"
        "CURATION(JSON): {curation}\n"
        "【輸出】\n"
        "嚴格輸出 JSON，必須符合 JuryOutput schema；不要多餘文字。"
    ),
    output_schema=JuryOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="jury_result",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
    before_agent_callback=_ensure_and_flatten_fallacies,
    after_agent_callback=jury_pretty_after,
)




