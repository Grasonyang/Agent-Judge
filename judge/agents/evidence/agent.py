from typing import List
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.genai import types

from judge.tools.evidence import Evidence
from judge.tools._state_record import record_agent_event


# ==== 查核結果資料模型 ====
class CheckedClaim(BaseModel):
    """單一句子與其證據鍊"""
    claim: str = Field(description="待查證的命題")
    evidences: List[Evidence] = Field(description="對應的證據鍊列表")


class EvidenceCheckOutput(BaseModel):
    """多條命題的查核結果"""
    checked_claims: List[CheckedClaim] = Field(description="查核後的命題與證據鍊")


# Step 1: 使用 Google 搜尋補齊證據
_evidence_tool_agent = LlmAgent(
    name="evidence_tool_runner",
    model="gemini-2.5-flash",
    instruction=(
        "根據辯論紀錄 state['debate_messages'] 或辯論檔案，"
        "使用 GoogleSearchTool 逐條查證並將搜尋結果寫入 state['evidence_raw']。"
    ),
    tools=[GoogleSearchTool()],
    output_key="evidence_raw",
)


# Step 2: 轉為結構化證據鍊 JSON
_evidence_schema_agent = LlmAgent(
    name="evidence_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "請整理 state['evidence_raw']，輸出符合 EvidenceCheckOutput 的 JSON。"
    ),
    output_schema=EvidenceCheckOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="evidence_checked",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# 公開的 Evidence Agent，先查詢再整理
evidence_agent = SequentialAgent(
    name="evidence_agent",
    sub_agents=[_evidence_tool_agent, _evidence_schema_agent],
)


def _record_evidence(agent_context=None, **_):
    if agent_context is None:
        return None
    state = agent_context.state
    sr = state.get("state_record_path")
    output = state.get("evidence_report") or state.get("evidence")
    record_agent_event(state, "evidence", {"type": "evidence", "payload": output}, sr)

evidence_agent.after_agent_callback = _record_evidence


# ensure debate_messages exists before running evidence agent
def _ensure_debate_messages(agent_context=None, **_):
    if agent_context is None:
        return None
    agent_context.state.setdefault("debate_messages", [])

evidence_agent.before_agent_callback = _ensure_debate_messages
