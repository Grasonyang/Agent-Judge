from typing import Optional
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.genai import types

# -------- Schema --------
class FactCheckInput(BaseModel):
    news_text: str = Field(description="待驗證的新聞文章內容")
    news_date: Optional[str] = Field(
        default=None,
        description="新聞發佈日期，若無則以今天的日期判斷"
    )

class FactCheckOutput(BaseModel):
    analysis: str = Field(description="完整分析結果")
    classification: str = Field(description="真假分類：「完全正確」、「部分正確」、「完全錯誤」、「完全錯誤」、「無法判斷」")

# -------- Agent 定義 --------
fact_check_tool_agent  = LlmAgent(
    name="fact_check_agent",
    model="gemini-2.5-flash",
    instruction=(
        "你現在在做假消息的判別，你是一個台灣人，需要做的事情是："
        "我會給你一篇待驗證真假的文章(news_text)，以及該篇文章的日期(news_date)。"
        "\n"
        "你的任務：\n"
        "1. 使用 GoogleSearchTool 查詢相關資料，盡量查詢台灣網站。\n"
        "2. 若分析出來的結果對不同族群有差異，請分別分析；若無，則針對整體分析。\n"
        "3. 請以 news_date 的時間作為判斷基準；若 news_date 為空，則以今天為準。\n"
        "4. 在輸出時，在每篇網站名稱後面加上該新聞的報導日期。\n"
        "5. 最後請給出結論，並歸類為：「完全正確」、「部分正確」、「完全錯誤」、「完全錯誤」、「無法判斷」。\n"
        "\n"
        "輸出格式：\n"
        "分析結果：[根據以上網站的分析與說明]\n"
        "真假分類：[「完全正確」、「部分正確」、「完全錯誤」、「完全錯誤」、「無法判斷」]"
    ),
    tools=[GoogleSearchTool()],
    #input_schema=FactCheckInput,
    #output_schema=FactCheckOutput,
    output_key="fact_check_result",
)

fact_check_schema_agent = LlmAgent(
    name="fact_check_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "你負責把 state['fact_check_raw'] 轉為符合 FactCheckOutput schema 的 JSON，"
        "分析文章 news_text，使用 news_date 作為判斷基準。"
        "僅輸出最終 JSON（不要多餘文字）。"
    ),
    #input_schema=FactCheckInput,
    output_schema=FactCheckOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="fact_check_result_json",
    generate_content_config=types.GenerateContentConfig(temperature=0.4),
)

# -------- Step 3: Sequential pipeline --------
llm_agent = SequentialAgent(
    name="fact_check_agent",
    sub_agents=[fact_check_tool_agent, fact_check_schema_agent],
)