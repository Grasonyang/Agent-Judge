from typing import List
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.genai import types

from judge.tools.evidence import Evidence


class CheckedClaim(BaseModel):
    claim: str = Field(description="待查證的命題")
    evidences: List[Evidence] = Field(description="對應的證據鍊列表")


class EvidenceCheckOutput(BaseModel):
    checked_claims: List[CheckedClaim] = Field(description="查核後的命題與證據鍊")


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


def _before_evidence(agent_context=None, **_):
    return None


evidence_agent = SequentialAgent(
    name="evidence_agent",
    sub_agents=[_evidence_tool_agent, _evidence_schema_agent],
    before_agent_callback=_before_evidence,
    after_agent_callback=None,
)

