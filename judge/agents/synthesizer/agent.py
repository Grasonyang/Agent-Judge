from typing import List, Optional
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from google.genai import types

# ===== 報告 Schema（ONLY JSON）=====
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


# ---------- 同 Jury：前置處理，建立 fallacy_list ----------
def _ensure_and_flatten_fallacies(callback_context=None, **_):
    # 確保在執行前已有辯論紀錄，並扁平化所有謬誤
    if callback_context is None:
        return None
    state = callback_context.state
    flat = []
    for msg in state["debate_messages"]:
        falls = msg.get("fallacies") if isinstance(msg, dict) else getattr(msg, "fallacies", None)
        if not falls:
            continue
        for f in falls:
            if hasattr(f, "model_dump"):
                flat.append(f.model_dump())
            else:
                flat.append(dict(f))
    state["fallacy_list"] = flat
    return None


# ===== Synthesizer：整合所有 JSON 成為 FinalReport JSON =====
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
    # 禁止傳遞以避免 output_schema 衝突
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="final_report_json",
    # planner removed to avoid sending thinking config to model
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
    before_agent_callback=_ensure_and_flatten_fallacies,
    after_agent_callback=None,
)

