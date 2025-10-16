# judge/agents/llm/fact_check_agent.py
"""
假新聞查核 Agent - 根據分類選擇不同 Prompt

核心想法: 用 Python 邏輯在 Agent 外部做路由,避免在 sub_agents 中使用 tools
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.genai import types

# -------- Schema --------
class FactCheckOutput(BaseModel):
    """假新聞查核的輸出 Schema"""
    category: str = Field(description="新聞類別")
    analysis: str = Field(description="完整分析結果")
    classification: str = Field(
        description="真假分類:「完全正確」、「部分正確」、「完全錯誤」、「無法判斷」"
    )


# -------- 不同類別的查核 Prompt --------
CATEGORY_PROMPTS = {
    "政治": """你是政治新聞查核專家。你是一個台灣人,需要做的事情是:

【任務】根據以下待驗證新聞進行假消息判別:
{_init_session}

【查核重點】
1. 使用 GoogleSearchTool 查詢相關資料,優先查詢:
   - 台灣政府官方網站
   - 國家級新聞媒體(中央社、聯合新聞網等)
   - 政治人物官方聲明

2. 特別注意:
   - 政治立場偏差:交叉比對不同立場媒體的報導
   - 查證政治人物發言時,務必找原始影片或逐字稿
   - 檢查發言內容是否被斷章取義

3. 在輸出時,在每篇網站名稱後面加上該新聞的報導日期

【輸出格式】
分析結果: [詳細分析過程與發現]
真假分類: [完全正確/部分正確/完全錯誤/無法判斷]""",

    "社會": """你是社會新聞查核專家。你是一個台灣人,需要做的事情是:

【任務】根據以下待驗證新聞進行假消息判別:
{_init_session}

【查核重點】
1. 使用 GoogleSearchTool 查詢相關資料,優先查詢:
   - 警政署、消防署等官方網站
   - 地方政府警察局
   - 地方媒體和國家級媒體的官方報導

2. 特別注意:
   - 犯罪、災害新聞必須確認官方證實
   - 檢查是否有誇大或虛構成分
   - 保護當事人隱私,避免散播未經證實的個人資訊
   - 核查死傷人數、地點等具體數字

3. 在輸出時,在每篇網站名稱後面加上該新聞的報導日期

【輸出格式】
分析結果: [詳細分析過程與發現]
真假分類: [完全正確/部分正確/完全錯誤/無法判斷]""",

    "國際": """你是國際新聞查核專家。你是一個台灣人,需要做的事情是:

【任務】根據以下待驗證新聞進行假消息判別:
{_init_session}

【查核重點】
1. 使用 GoogleSearchTool 查詢相關資料,優先查詢:
   - BBC, Reuters, AP, AFP 等國際主流媒體
   - 相關國家的官方新聞機構
   - 當地獨立新聞媒體

2. 特別注意:
   - 不同國家媒體的報導角度差異
   - 檢查消息來源是否可靠
   - 對於戰爭、外交等敏感議題,交叉比對多方來源
   - 查證國際組織(UN, WHO等)的官方聲明

3. 在輸出時,在每篇網站名稱後面加上該新聞的報導日期

【輸出格式】
分析結果: [詳細分析過程與發現]
真假分類: [完全正確/部分正確/完全錯誤/無法判斷]""",

    "財經": """你是財經新聞查核專家。你是一個台灣人,需要做的事情是:

【任務】根據以下待驗證新聞進行假消息判別:
{_init_session}

【查核重點】
1. 使用 GoogleSearchTool 查詢相關資料,優先查詢:
   - 金融監督管理委員會(FSC)
   - 臺灣証券交易所
   - 各公司官方投資者關係網站
   - 財經專業媒體

2. 特別注意:
   - 股市、投資建議是否為詐騙或誤導資訊
   - 公司財報、股價等數據必須以官方公告為準
   - 檢查是否有內線交易或市場操縱的跡象
   - 驗證公司重大公告的真實性

3. 在輸出時,在每篇網站名稱後面加上該新聞的報導日期

【輸出格式】
分析結果: [詳細分析過程與發現]
真假分類: [完全正確/部分正確/完全錯誤/無法判斷]""",

    "科技": """你是科技新聞查核專家。你是一個台灣人,需要做的事情是:

【任務】根據以下待驗證新聞進行假消息判別:
{_init_session}

【查核重點】
1. 使用 GoogleSearchTool 查詢相關資料,優先查詢:
   - 科技公司官方網站、新聞稿
   - 技術文件和官方說明
   - 科技媒體的評測和報導

2. 特別注意:
   - 產品規格、技術細節以官方發布為準
   - 區分「未經證實的傳聞」與「官方證實」的資訊
   - 檢查是否有過度宣傳或虛假承諾
   - 驗證產品發布日期和上市時間

3. 在輸出時,在每篇網站名稱後面加上該新聞的報導日期

【輸出格式】
分析結果: [詳細分析過程與發現]
真假分類: [完全正確/部分正確/完全錯誤/無法判斷]""",

    "default": """你是新聞查核專家。你是一個台灣人,需要做的事情是:

【任務】根據以下待驗證新聞進行假消息判別:
{_init_session}

【查核重點】
1. 使用 GoogleSearchTool 查詢相關資料,盡量查詢台灣網站和官方來源

2. 若分析出來的結果對不同族群有差異,請分別分析;若無,則針對整體分析

3. 在輸出時,在每篇網站名稱後面加上該新聞的報導日期

【輸出格式】
分析結果: [詳細分析過程與發現]
真假分類: [完全正確/部分正確/完全錯誤/無法判斷]"""
}


# -------- Step 1: 文本分類 Agent (純 LLM,無 tools) --------
classification_agent = LlmAgent(
    name="text_classification",
    model="gemini-2.5-flash",
    instruction=(
        "你是文本分類器。根據以下新聞文本,判斷其所屬類別。\n\n"
        "待分類文本: {_init_session}\n\n"
        "請判斷屬於以下哪一類:\n"
        "- 政治:涉及政治人物、政策、選舉等\n"
        "- 社會:涉及犯罪、災害、社會事件等\n"
        "- 國際:涉及國外新聞、國際關係等\n"
        "- 財經:涉及股市、公司、經濟等\n"
        "- 科技:涉及科技產品、技術發展等\n"
        "- 其他:生活、娛樂、體育等\n\n"
        "只輸出類別名稱,不要有其他文字。"
    ),
    output_key="text_classification",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# -------- Step 2: 建立所有類別的查核 Agent --------
def _create_category_check_agent(category: str, prompt: str) -> LlmAgent:
    """根據類別和 prompt 建立查核 Agent"""
    return LlmAgent(
        name=f"fact_check_{category}",
        model="gemini-2.5-flash",
        instruction=prompt,
        tools=[GoogleSearchTool()],
        output_key="fact_check_result",
        generate_content_config=types.GenerateContentConfig(temperature=0.4),
    )


# 建立各類別的 Agent 實例
category_agents = {
    category: _create_category_check_agent(category, prompt)
    for category, prompt in CATEGORY_PROMPTS.items()
    if category != "default"
}
category_agents["default"] = _create_category_check_agent("default", CATEGORY_PROMPTS["default"])


# -------- Step 3: Schema 驗證 Agent (純 LLM,無 tools) --------
schema_validator_agent = LlmAgent(
    name="fact_check_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "你是 Schema 驗證器。\n\n"
        "識別的新聞類別: {text_classification}\n"
        "查核結果: {fact_check_result}\n\n"
        "請從查核結果中提取:\n"
        "1. category: 識別出的新聞類別\n"
        "2. analysis: 完整的分析結果(包含查證過程和發現)\n"
        "3. classification: 真假分類結論\n\n"
        "輸出為嚴格的 JSON 格式,僅包含這三個欄位。\n"
        "輸出: {\"category\": \"...\", \"analysis\": \"...\", \"classification\": \"...\"}\n"
        "只輸出 JSON,不要有任何多餘文字。"
    ),
    output_schema=FactCheckOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="fact_check_result_json",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# -------- 自訂 Agent:使用 Python 邏輯做路由 --------
class DynamicFactCheckAgent(LlmAgent):
    """
    動態假新聞查核 Agent
    
    核心原理:
    1. 先用 classification_agent 分類新聞
    2. 根據分類結果,在 Python 中選擇對應的 category_agent
    3. 執行選中的 agent
    4. 最後用 schema_validator_agent 格式化
    
    這樣避免了在 sub_agents 中使用 tools 的問題!
    """
    classification_agent: Optional[Any] = None  # ✅ 新增這一行
    category_agents: Optional[Any] = None   # ✅ 新增這一行
    schema_agent: Optional[Any] = None   # ✅ 新增這一行
    def __init__(self):
        super().__init__(
            name="dynamic_fact_check",
            model="gemini-2.5-flash",
            instruction="協調者 Agent(內部使用,實際工作由其他 Agent 完成)",
            output_key="orchestration_log",
        )
        self.classification_agent = classification_agent
        self.category_agents = category_agents
        self.schema_agent = schema_validator_agent
    
    async def run_async(self, news_text: str, agent_context=None) -> Dict[str, Any]:
        """執行動態路由的查核 Pipeline"""
        
        
        print("\n🚀 開始假新聞查核 Pipeline...\n")
        
        # Step 1: 分類
        print("📊 [步驟1/3] 正在分類新聞類別...")
        classification_result = await self.classification_agent.run_async(news_text)
        category = classification_result.get("text_classification", "default").strip()
        print(f"✅ 分類結果: {category}\n")
        
        # 更新 state
        if agent_context and hasattr(agent_context, 'state'):
            agent_context.state["text_classification"] = category
        
        # Step 2: 根據分類選擇對應的查核 Agent
        print(f"🔍 [步驟2/3] 使用 {category} 類別專屬策略進行查核...\n")
        selected_agent = self.category_agents.get(category, self.category_agents["default"])
        
        fact_check_result = await selected_agent.run_async(news_text)
        fact_check_text = fact_check_result.get("fact_check_result", "查核失敗")
        print("✅ 查核完成\n")
        
        # 更新 state
        if agent_context and hasattr(agent_context, 'state'):
            agent_context.state["fact_check_result"] = fact_check_text
        
        # Step 3: 格式化輸出
        print("📄 [步驟3/3] 正在格式化輸出...\n")
        formatted_result = await self.schema_agent.run_async(
            f"分類: {category}\n查核結果: {fact_check_text}"
        )
        final_output = formatted_result.get("fact_check_result_json", "")
        
        # 更新 state - 關鍵!
        if agent_context and hasattr(agent_context, 'state'):
            agent_context.state["fact_check_result_json"] = final_output
        
        print("✅ 假新聞查核完成!\n")
        print("=" * 70)
        
        return {
            "fact_check_result_json": final_output,
            "text_classification": category,
        }


# -------- 建立用於 Judge 系統的 Sequential Pipeline --------
# 這個是給 ADK 使用的
fact_check_agent = SequentialAgent(
    name="fact_check_pipeline",
    sub_agents=[
        classification_agent,      # Step 1: 純 LLM 分類(無 tools)
        # 注意: 我們不在這裡放 category agents,因為要避免 tools 問題
        # 而是在 DynamicFactCheckAgent 中用 Python 邏輯處理
    ],
)


__all__ = [
    "fact_check_agent",
    "DynamicFactCheckAgent",
    "FactCheckOutput",
    "category_agents",
]