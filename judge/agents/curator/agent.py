from typing import List, Optional
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types

# ✨ 內建搜尋工具
from google.adk.tools.google_search_tool import GoogleSearchTool
# 採用絕對匯入以確保 Evidence 類別在各層級皆可正確引用
from judge.tools.evidence import Evidence
from functools import partial
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions


# -------- Schema（輸入/輸出）---------
class CuratorInput(BaseModel):
    query: str = Field(description="搜尋查詢關鍵字或問題")
    top_k: int = Field(default=5, description="回傳前幾筆結果（1~10 建議）")
    site: Optional[str] = Field(
        default=None,
        description="可選的站點過濾，如 'site:reuters.com' 或 'site:gov.tw'",
    )

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

    def to_evidence(
        self,
        claim: str,
        warrant: str,
        method: Optional[str] = None,
        risk: Optional[str] = None,
        confidence: Optional[str] = None,
    ) -> Evidence:
        """轉為 Evidence 方便其他代理引用"""
        # 使用 Evidence 模型建立標準化證據物件
        return Evidence(
            source=self.url,
            claim=claim,
            warrant=warrant,
            method=method,
            risk=risk,
            confidence=confidence,
        )

class CuratorOutput(BaseModel):
    query: str
    results: List[SearchResult]


# -------- LLM Agent 定義 --------
# --- Step 1: tool-only agent that writes raw search output to state['curation_raw'] ---
curator_tool_agent = LlmAgent(
    name="curator_tool_runner",
    model="gemini-2.5-flash",
    instruction=(
        "你是 Curator 的工具執行者：使用 GoogleSearchTool 來取得原始搜尋結果，"
        "請把原始結果（未经 schema 驗證的 JSON）存入 state['curation_raw']。"
    ),
    tools=[GoogleSearchTool()],
    # 不設 output_schema（工具原始輸出）
    output_key="curation_raw",
    # planner removed to avoid sending thinking config to model
)


# --- Step 2: schema-validator agent (no tools) that reads state['curation_raw'] and emits validated state['curation'] ---
curator_schema_agent = LlmAgent(
    name="curator_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "你負責把 state['curation_raw'] 轉為符合 CuratorOutput schema 的 JSON，"
        "僅輸出最終的 JSON（不要多餘文字）。"
    ),
    # no tools here
    input_schema=CuratorInput,
    output_schema=CuratorOutput,
    # 禁止輸出傳遞以避免與 schema 衝突
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="curation",
    # planner removed to avoid sending thinking config to model
    generate_content_config=types.GenerateContentConfig(temperature=0.4),
)


# --- Public curator_pipeline: run tool agent then schema validator sequentially ---
curator_agent = SequentialAgent(
    name="curator",
    sub_agents=[curator_tool_agent, curator_schema_agent],
)


def _record_curator(agent_context=None, append_event=None, **_):
    if agent_context is None or append_event is None:
        return None
    state = agent_context.state
    output = state.get("curation")
    append_event(
        Event(
            author="curator",
            actions=EventActions(state_delta={"curation": output}),
        )
    )


def register_session(append_event):
    curator_agent.after_agent_callback = partial(_record_curator, append_event=append_event)

