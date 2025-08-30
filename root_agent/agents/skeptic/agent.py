from typing import List
from pydantic import BaseModel, Field, ValidationError

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from google.adk.tools.google_search_tool import GoogleSearchTool
from ..evidence import Evidence


# ---- 方便比對 Advocate / Curator 內容 ----
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


# ---- Skeptic 輸出 Schema（ONLY JSON） ----
class SkepticOutput(BaseModel):
    counter_thesis: str = Field(description="反方的核心反命題（單句）")
    challenges: List[str] = Field(description="逐點質疑，最好對應正方 key_points 的編號或重點")
    evidence: List[Evidence] = Field(description="反向或修正的證據")
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


# Step 2: schema-only agent that consumes state['curation'], state['advocacy'] 和 state['skeptic_search_raw']，並輸出符合 SkepticOutput 的 JSON
skeptic_schema_agent = LlmAgent(
    name="skeptic_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "請根據 state['curation'] 與 state['advocacy']，以及可選的 state['skeptic_search_raw'] 補充，"
        "輸出符合 SkepticOutput schema 的 JSON（不使用任何工具）。"
    ),
    # 無需工具
    output_schema=SkepticOutput,
    output_key="skepticism",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# Public skeptic pipeline with simple retry for schema validation
class SkepticSequentialAgent(SequentialAgent):
    async def run_async(self, session):
        # 先執行工具代理人
        await self.sub_agents[0].run_async(session)

        last_error = None
        # 最多嘗試兩次產生符合 Schema 的結果
        for _ in range(2):
            try:
                await self.sub_agents[1].run_async(session)
                # 驗證是否符合 SkepticOutput
                SkepticOutput.model_validate(session.state["skepticism"])
                return
            except (ValidationError, ValueError, KeyError) as e:
                # 記錄錯誤並重試
                last_error = e
        # 若仍失敗則拋出錯誤
        raise last_error


skeptic_agent = SkepticSequentialAgent(
    name="skeptic",
    sub_agents=[skeptic_tool_agent, skeptic_schema_agent],
)
