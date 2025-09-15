from typing import List, Optional
from pydantic import BaseModel, Field
from judge.tools.evidence import Evidence
from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from google.adk.tools.google_search_tool import GoogleSearchTool

# -------- Schema（定義供他處參考；本步不綁定 output_schema，以避免「tools+schema」衝突）---------
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

# -------- 單一步：用工具，但「不」啟用 output_schema；直接輸出乾淨 JSON --------
curator_tool_agent = LlmAgent(
    name="curator_runner",
    model="gemini-2.5-flash",
    instruction=(
        "你是 Curator。請依下列規則完成搜尋與輸出：\n"
        "1) 視需要呼叫 GoogleSearchTool 進行搜尋；可在查詢字串使用 site:, -filetype:, intitle:, inurl: 等運算子。\n"
        "2) 整理並『只』輸出以下 JSON，且不得含有其他任何文字：\n"
        "{\n"
        "  \"query\": string,\n"
        "  \"results\": [ { \"title\": string, \"url\": string, \"snippet\": string }, ... ]\n"
        "}\n"
        "3) 白名單鍵嚴格限制為：query、results[].title、results[].url、results[].snippet。\n"
        "4) results 最多保留 top_k 筆（預設5、最大10）。snippet 最長約 240 字，必要時在語義完整處截斷。\n"
        "5) 嚴禁將任何 HTML/CSS/JS、圖片或 Google Grounding/UI 欄位（如 renderedContent、groundingMetadata、widgets）納入輸出或寫入狀態。"
    ),
    tools=[GoogleSearchTool()],
    input_schema=CuratorInput,
    # 不設定 output_schema，否則會和 tools 衝突
    output_key="curation",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.4,
        max_output_tokens=1200,      # 控制長度，避免長文
    ),
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

curator_agent = SequentialAgent(
    name="curator",
    sub_agents=[curator_tool_agent],
)