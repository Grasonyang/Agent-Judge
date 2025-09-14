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
    thesis: str
    key_points: List[str]
    evidence: List[Evidence]
    caveats: List[str]


class SkepticOutput(BaseModel):
    counter_thesis: str = Field(description="反方的核心反命題（單句）")
    challenges: List[str] = Field(description="逐點質疑，最好對應正方 key_points 的編號或重點")
    evidence: List[Evidence] = Field(description="反向或修正的證據")
    open_questions: List[str] = Field(description="尚無定論、需要進一步查證的問題點")


skeptic_tool_agent = LlmAgent(
    name="skeptic_tool_runner",
    model="gemini-2.5-flash",
    instruction=(
        "你是 Skeptic 的工具執行者：在需要時使用 GoogleSearchTool 搜尋反證，"
        "並把工具輸出寫入 state['skeptic_search_raw']。"
    ),
    tools=[GoogleSearchTool()],
    output_key="skeptic_search_raw",
)


skeptic_schema_agent = LlmAgent(
    name="skeptic_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "請根據 state['curation'] 與 state['advocacy']，以及可選的 state['skeptic_search_raw'] 補充，"
        "輸出符合 SkepticOutput schema 的 JSON（不使用任何工具）。"
    ),
    output_schema=SkepticOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="skepticism",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

skeptic_agent = SequentialAgent(
    name="skeptic",
    sub_agents=[skeptic_tool_agent, skeptic_schema_agent],
)

