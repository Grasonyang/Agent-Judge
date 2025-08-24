from typing import List, Optional
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from google.adk.tools.google_search_tool import GoogleSearchTool


# ---- 讀 Curator 的證據結構（最小鏡像；如你已有型別可改 from ... import） ----
class CuratorSearchResult(BaseModel):
    title: str
    url: str
    snippet: str

class CuratorOutput(BaseModel):
    query: str
    # 如果你的 Curator 有 final_query 也可加上
    results: List[CuratorSearchResult]


# ---- Advocate 輸出 Schema（ONLY JSON） ----
class EvidenceUse(BaseModel):
    title: str
    url: str
    why_relevant: str
    quote_or_fact: Optional[str] = None  # 可選：引用片段或關鍵事實（簡短）

class AdvocateOutput(BaseModel):
    thesis: str = Field(description="正方主張的核心命題（單句）")
    key_points: List[str] = Field(description="3~6 條支持重點，避免冗長")
    evidence_used: List[EvidenceUse] = Field(description="逐條列出引用了哪些證據與理由")
    caveats: List[str] = Field(description="已知限制或尚待查證處（1~3 條）")


# ---- Advocate 定義 ----
# Step 1: tool-only agent to allow optional additional searches; write raw search outputs to state
advocate_tool_agent = LlmAgent(
    name="advocate_tool_runner",
    model="gemini-2.5-flash",
    instruction=(
        "你是 Advocate 的工具執行者：在需要時使用 GoogleSearchTool 補充證據，"
        "並把任何工具輸出（raw）寫入 state['advocate_search_raw']。"
    ),
    tools=[GoogleSearchTool()],
    output_key="advocate_search_raw",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=256)
    ),
)


# Step 2: schema-only agent that consumes state['curation'] and state['advocate_search_raw'] to produce validated advocacy
advocate_schema_agent = LlmAgent(
    name="advocate_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "根據 state['curation']（Curator 的結果）與可選的 state['advocate_search_raw'] 補充，"
        "輸出符合 AdvocateOutput schema 的 JSON。"
    ),
    # no tools here
    output_schema=AdvocateOutput,
    output_key="advocacy",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=256)
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.4),
)


# Public advocate pipeline
advocate_agent = SequentialAgent(
    name="advocate",
    sub_agents=[advocate_tool_agent, advocate_schema_agent],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=256)
    ),
)
