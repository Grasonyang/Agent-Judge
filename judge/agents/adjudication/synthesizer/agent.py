from typing import List, Optional
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
import json
from google.genai import types
from judge.tools import flatten_fallacies


class StakeSummary(BaseModel):
    side: str = Field(description="立場/角色，如 'Advocate'、'Skeptic'、'Devil'")
    thesis: str = Field(description="該方核心主張（或反主張）")
    strongest_points: List[str] = Field(description="2~5 條最強論點")
    weaknesses: List[str] = Field(description="2~5 條主要缺口/疑慮")


class Contention(BaseModel):
    question: str = Field(description="爭點問題（單句）")
    what_advocates_say: List[str]
    what_skeptics_say: List[str]
    what_devil_pushed: List[str] = Field(default_factory=list)
    status: str = Field(description="綜合判斷：共識 / 爭議中 / 證據不足 等")


class RiskItem(BaseModel):
    name: str
    why: str
    mitigation: Optional[str] = None


class FinalReport(BaseModel):
    topic: str
    overall_assessment: str = Field(description="總結一句話：可信度/爭議度/建議行動")
    jury_score: Optional[int] = Field(default=None, description="Jury total 0~100，如有")
    jury_brief: Optional[str] = Field(default=None, description="Jury 的簡短摘要")
    evidence_digest: List[str] = Field(description="最關鍵證據/來源 3~8 條（含網址簡述）")
    stake_summaries: List[StakeSummary] = Field(description="各方重點總結")
    key_contentions: List[Contention] = Field(description="2~4 個核心爭點")
    risks: List[RiskItem] = Field(default_factory=list, description="可選：風險與緩解")
    open_questions: List[str] = Field(default_factory=list)
    appendix_links: List[str] = Field(default_factory=list, description="附錄連結（辯論日誌/原始證據等）")


def _ensure_and_flatten_fallacies(callback_context=None, **_):
    if callback_context is None:
        return None
    state = callback_context.state
    msgs = state.get("debate_messages") or []
    state["debate_messages"] = msgs
    state["fallacy_list"] = flatten_fallacies(msgs)
    return None


def _pretty_after(agent_context=None, **_):
    if agent_context is None:
        return None
    st = agent_context.state
    out = st.get("final_report_json")
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
    return Event(author="synthesizer", actions=EventActions(message=msg))


synthesizer_agent = LlmAgent(
    name="synthesizer",
    model="gemini-2.5-flash",
    instruction=(
        "你是『知識整合者（Synthesizer）』。根據下列輸入生成最終報告的嚴格 JSON。\n\n"
        "【輸入】\n"
        "- CURATION(JSON): {curation}\n"
        "- ADVOCACY(JSON): (the current advocacy JSON in state['advocacy'], if any)\n"
        "- SKEPTICISM(JSON): (the current skepticism JSON in state['skepticism'], if any)\n"
        "- (可選) DEVIL(JSON): (the optional devil turn stored in state['devil_turn'], if any)\n"
        "- JURY(JSON): (the current jury result in state['jury_result'], if any)\n"
        "- DEBATE LOG (messages array): (the current debate messages stored in state['debate_messages'])\n"
        "- SOCIAL LOG(JSON): (the current social diffusion log stored in state['social_log'], if any)\n\n"
        "【要求】\n"
        "1) 僅輸出符合 FinalReport schema 的 JSON；不得有多餘文字。\n"
        "2) overall_assessment 要清楚可執行；evidence_digest 列出最關鍵來源（含短說明、可附 URL）。\n"
        "3) key_contentions 需能對照正反雙方觀點；若 devil_turn 存在，整合在 what_devil_pushed。\n"
        "4) 若有 jury_result，填入 jury_score 與簡短 jury_brief（30 字內）。\n"
        "5) appendix_links 可放『辯論日誌』或外部來源列表連結（若有）。"
    ),
    output_schema=FinalReport,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="final_report_json",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
    before_agent_callback=_ensure_and_flatten_fallacies,
    after_agent_callback=_pretty_after,
)
