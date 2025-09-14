from typing import List, Optional
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from google.adk.tools.google_search_tool import GoogleSearchTool
from judge.tools.evidence import Evidence


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


curator_tool_agent = LlmAgent(
    name="curator_tool_runner",
    model="gemini-2.5-flash",
    instruction=(
        "你是 Curator 的工具執行者：使用 GoogleSearchTool 來取得原始搜尋結果，"
        "請把原始結果（未经 schema 驗證的 JSON）存入 state['curation_raw']。"
    ),
    tools=[GoogleSearchTool()],
    output_key="curation_raw",
)


curator_schema_agent = LlmAgent(
    name="curator_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "你負責把 state['curation_raw'] 轉為符合 CuratorOutput schema 的 JSON，"
        "僅輸出最終的 JSON（不要多餘文字）。"
    ),
    input_schema=CuratorInput,
    output_schema=CuratorOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="curation",
    generate_content_config=types.GenerateContentConfig(temperature=0.4),
)


curator_agent = SequentialAgent(
    name="curator",
    sub_agents=[curator_tool_agent, curator_schema_agent],
)

