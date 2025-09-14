from typing import List
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
import json
from google.genai import types
from judge.tools import flatten_fallacies


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
    scores: ScoreDetail
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
    model="gemini-2.5-flash",
    instruction=(
        "你是陪審團，請根據完整辯論紀錄與證據，進行客觀量化評分並給出裁決。\n\n"
        "【輸入】\n"
        "CURATION(JSON): {curation}\n"
        "ADVOCACY(JSON): (the current advocacy JSON in state['advocacy'], if any)\n"
        "SKEPTICISM(JSON): (the current skepticism JSON in state['skepticism'], if any)\n"
        "DEBATE(LOG): (the current debate messages stored in state['debate_messages'])\n"
        "SOCIAL_LOG(JSON): {social_log}\n\n"
        "【評分規則】\n"
        "- evidence_quality: 來源權威性/時效性/相關性（0~30）\n"
        "- logical_rigor: 是否自洽、是否有謬誤（0~30）\n"
        "- robustness: 面對反駁與極端質疑的韌性（0~20）\n"
        "- social_impact: 根據 SOCIAL_LOG 中的反應評估潛在影響與擾動（0~20）\n"
        "合計 total 0~100。\n\n"
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
