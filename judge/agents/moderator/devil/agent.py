from typing import List
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from google.adk.tools.google_search_tool import GoogleSearchTool
from judge.tools.evidence import Evidence


class DevilOutput(BaseModel):
    stance: str = Field(description="極端質疑的核心立場，單句")
    attack_points: List[str] = Field(description="2~5 條攻擊點，盡量尖銳")
    evidence: List[Evidence] = Field(description="引用或質疑的證據列表")
    requested_clarifications: List[str] = Field(description="希望對方補充/舉證的關鍵問題")


devil_tool_agent = LlmAgent(
    name="devil_tool_runner",
    model="gemini-2.5-flash",
    instruction=(
        "你是 Devil 的工具執行者：在需要時使用 GoogleSearchTool 補充證據，"
        "並把任何工具輸出（raw）寫入 state['devil_search_raw']。"
    ),
    tools=[GoogleSearchTool()],
    output_key="devil_search_raw",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


devil_schema_agent = LlmAgent(
    name="devil_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "根據 state['curation']、state['debate_messages'] 與可選的 state['devil_search_raw']，"
        "輸出符合 DevilOutput schema 的嚴格 JSON（不要多餘文字）。"
    ),
    output_schema=DevilOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="devil_turn",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


def _before_devil(agent_context=None, **_):
    return None


devil_agent = SequentialAgent(
    name="devils_advocate",
    sub_agents=[devil_tool_agent, devil_schema_agent],
    before_agent_callback=_before_devil,
    after_agent_callback=None,
)

