# judge/agents/llm/agent.py - 完整修正版

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext 
from google.genai import types
from google.adk.events.event_actions import EventActions
from google.adk.events.event import Event

from .fact_check_agent import (
    classification_agent,
    category_agents,
    schema_validator_agent,
)


# ========== Step 1: 純分類 Agent (無 tools) ==========
text_classifier = LlmAgent(
    name="text_classifier",
    model="gemini-2.0-flash",
    instruction=(
        "你是文本分類器。根據以下新聞文本，判斷其所屬類別。\n\n"
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


# ========== Step 2: 根據分類選擇對應的查核 Agent ==========
CATEGORY_TO_AGENT = {
    "政治": category_agents.get("政治"),
    "社會": category_agents.get("社會"),
    "國際": category_agents.get("國際"),
    "財經": category_agents.get("財經"),
    "科技": category_agents.get("科技"),
    "其他": category_agents.get("default"),
    "default": category_agents.get("default"),
}


# ========== Step 3: 動態路由 Agent (核心邏輯) ==========
class DynamicRoutingAgent(BaseAgent):
    """
    核心邏輯：
    1. 先執行分類
    2. 根據分類結果選擇對應的查核 Agent
    3. 執行查核
    4. 格式化輸出
    """
    
    async def run_async(self, query: str, agent_context: CallbackContext | None = None, **kwargs):
        """動態路由和條件執行"""
        
        if agent_context is None:
            return
        
        state = agent_context.state
        news_text = state.get("_init_session", query)
        
        print("\n" + "=" * 70)
        print("🚀 開始動態假新聞查核 Pipeline...")
        print("=" * 70)
        
        # ✅ Step 1: 分類
        print("\n📊 [步驟1/4] 正在分類新聞類別...")
        yield agent_context.event_builder(
            author="dynamic_routing",
            message="Step 1: Classifying news content...",
            actions=EventActions(state_delta={"pipeline_step": "Classification"})
        ).build()
        
        try:
            # 執行分類 Agent
            async for classification_event in text_classifier.run_async(news_text, agent_context):
                yield classification_event
            
            category = state.get("text_classification", "default").strip()
            print(f"✅ 分類結果: {category}\n")
            
            yield agent_context.event_builder(
                author="dynamic_routing",
                message=f"Classified as: {category}",
                actions=EventActions(state_delta={"classification_result": category})
            ).build()
            
        except Exception as e:
            print(f"❌ 分類失敗: {e}")
            yield agent_context.event_builder(
                author="dynamic_routing",
                message=f"Classification failed: {e}",
                actions=EventActions(state_delta={"pipeline_error": str(e)})
            ).build()
            return
        
        # ✅ Step 2: 根據分類選擇查核 Agent
        print(f"🔍 [步驟2/4] 選擇 '{category}' 類別專屬查核策略...\n")
        selected_agent = CATEGORY_TO_AGENT.get(category, CATEGORY_TO_AGENT["default"])
        
        if selected_agent is None:
            print(f"⚠️ 未找到 '{category}' 對應的 Agent，使用預設策略")
            selected_agent = CATEGORY_TO_AGENT["default"]
        
        yield agent_context.event_builder(
            author="dynamic_routing",
            message=f"Step 2: Using {category}-specific checking strategy...",
            actions=EventActions(state_delta={"pipeline_step": f"Fact-check ({category})"})
        ).build()
        
        # ✅ Step 3: 執行對應的查核 Agent
        print(f"📝 [步驟3/4] 執行 {category} 類別查核...\n")
        try:
            async for fact_check_event in selected_agent.run_async(news_text, agent_context):
                yield fact_check_event
            
            print("✅ 查核完成\n")
            
        except Exception as e:
            print(f"❌ 查核失敗: {e}")
            yield agent_context.event_builder(
                author="dynamic_routing",
                message=f"Fact-check failed: {e}",
                actions=EventActions(state_delta={"pipeline_error": str(e)})
            ).build()
            return
        
        # ✅ Step 4: 格式化輸出
        print("📄 [步驟4/4] 正在格式化輸出...\n")
        try:
            async for schema_event in schema_validator_agent.run_async(
                f"分類: {category}\n查核結果: {state.get('fact_check_result', '')}",
                agent_context
            ):
                yield schema_event
            
            print("✅ 假新聞查核完成!\n")
            print("=" * 70 + "\n")
            
            yield agent_context.event_builder(
                author="dynamic_routing",
                message="Fact-check completed successfully",
                actions=EventActions(state_delta={
                    "pipeline_step": "Completed",
                    "pipeline_status": "success"
                })
            ).build()
            
        except Exception as e:
            print(f"❌ 格式化失敗: {e}")
            yield agent_context.event_builder(
                author="dynamic_routing",
                message=f"Schema validation failed: {e}",
                actions=EventActions(state_delta={"pipeline_error": str(e)})
            ).build()


# ========== 最終導出 ==========
dynamic_fact_check = DynamicRoutingAgent(name="dynamic_fact_check")

__all__ = [
    "dynamic_fact_check",
    "text_classifier",
    "CATEGORY_TO_AGENT",
]