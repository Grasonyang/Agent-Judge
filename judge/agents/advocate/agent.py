from typing import List
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from google.adk.tools.google_search_tool import GoogleSearchTool
from judge.tools.evidence import Evidence
from functools import partial
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions


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
class AdvocateOutput(BaseModel):
    thesis: str = Field(description="正方主張的核心命題（單句）")
    key_points: List[str] = Field(description="3~6 條支持重點，避免冗長")
    evidence: List[Evidence] = Field(description="逐條列出引用的證據")
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
    # planner removed to avoid sending thinking config to model
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
    # 設為禁止傳遞以符合 output_schema 限制
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="advocacy",
    # planner removed to avoid sending thinking config to model
    generate_content_config=types.GenerateContentConfig(temperature=0.4),
)


def _record_advocacy(agent_context=None, append_event=None, **_):
    """after_agent_callback to append advocacy output to state_record if available"""
    if agent_context is None or append_event is None:
        return None
    state = agent_context.state
    output = state.get("advocacy")
    # 使用 Session 事件記錄最新的正方輸出
    append_event(
        Event(
            author="advocate",
            actions=EventActions(state_delta={"advocacy": output}),
        )
    )


def register_session(append_event):
    advocate_schema_agent.after_agent_callback = partial(
        _record_advocacy, append_event=append_event
    )


# Public advocate pipeline
advocate_agent = SequentialAgent(
    name="advocate",
    sub_agents=[advocate_tool_agent, advocate_schema_agent],
)
