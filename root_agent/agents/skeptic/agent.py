from typing import List, Optional
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from google.adk.tools.google_search_tool import GoogleSearchTool


# ---- 方便比對 Advocate / Curator 內容 ----
class CuratorSearchResult(BaseModel):
    title: str
    url: str
    snippet: str

class CuratorOutput(BaseModel):
    query: str
    results: List[CuratorSearchResult]

class EvidenceUse(BaseModel):
    title: str
    url: str
    why_relevant: str
    quote_or_fact: Optional[str] = None

class AdvocateOutput(BaseModel):
    thesis: str
    key_points: List[str]
    evidence_used: List[EvidenceUse]
    caveats: List[str]


# ---- Skeptic 輸出 Schema（ONLY JSON） ----
class CounterEvidence(BaseModel):
    title: str
    url: str
    how_it_refutes: str
    quote_or_fact: Optional[str] = None

class SkepticOutput(BaseModel):
    counter_thesis: str = Field(description="反方的核心反命題（單句）")
    challenges: List[str] = Field(description="逐點質疑，最好對應正方 key_points 的編號或重點")
    counter_evidence: List[CounterEvidence] = Field(description="反向或修正的證據")
    open_questions: List[str] = Field(description="尚無定論、需要進一步查證的問題點")


# ---- Skeptic 定義 ----
# Step 1: tool-only agent to optionally search for counter-evidence; write raw outputs to state['skeptic_search_raw']
skeptic_tool_agent = LlmAgent(
    name="skeptic_tool_runner",
    model="gemini-2.5-flash",
    instruction=(
        "你是 Skeptic 的工具執行者：在需要時使用 GoogleSearchTool 搜尋反證，"
        "並把工具輸出寫入 state['skeptic_search_raw']。"
    ),
    tools=[GoogleSearchTool()],
    output_key="skeptic_search_raw",
    # planner removed to avoid sending thinking config to model
)


# Step 2: schema-only agent that consumes state['curation'], state['advocacy'] and state['skeptic_search_raw'] to produce validated skepticism
skeptic_schema_agent = LlmAgent(
    name="skeptic_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "請根據 state['curation'] 與 state['advocacy']，以及可選的 state['skeptic_search_raw'] 補充，"
        "輸出符合 SkepticOutput schema 的 JSON（不使用任何工具）。"
    ),
    # no tools here
    # remove output_schema to avoid validation errors from imperfect JSON
    # instead write raw/structured output to state['skepticism']
    output_key="skepticism",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# Public skeptic pipeline
skeptic_agent = SequentialAgent(
    name="skeptic",
    sub_agents=[skeptic_tool_agent, skeptic_schema_agent],
)
