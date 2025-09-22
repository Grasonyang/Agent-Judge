from typing import List
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from google.adk.tools.google_search_tool import GoogleSearchTool
from judge.tools.evidence import Evidence


class CuratorSearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class CuratorOutput(BaseModel):
    query: str
    results: List[CuratorSearchResult]


class AdvocateOutput(BaseModel):
    thesis: str = Field(description="正方主張的核心命題（單句）")
    key_points: List[str] = Field(description="3~6 條支持重點，避免冗長")
    evidence: List[Evidence] = Field(description="逐條列出引用的證據")
    caveats: List[str] = Field(description="已知限制或尚待查證處（1~3 條）")


advocate_tool_agent = LlmAgent(
    name="advocate_tool_runner",
    model="gemini-2.5-flash",
    instruction=(
        "你是 Advocate 的工具執行者：在需要時使用 GoogleSearchTool 補充證據，"
        "並把任何工具輸出（raw）寫入 state['advocate_search_raw']。"
    ),
    tools=[GoogleSearchTool()],
    output_key="advocate_search_raw",
)


advocate_schema_agent = LlmAgent(
    name="advocate_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "根據 state['curation']（Curator 的結果）與可選的 state['advocate_search_raw'] 補充，"
        "輸出符合 AdvocateOutput schema 的 JSON。"
    ),
    output_schema=AdvocateOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="advocacy",
    generate_content_config=types.GenerateContentConfig(temperature=0.4),
)


advocate_agent = SequentialAgent(
    name="advocate",
    sub_agents=[advocate_tool_agent, advocate_schema_agent],
)

