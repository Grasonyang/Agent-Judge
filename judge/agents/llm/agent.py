# judge/agents/llm/agent.py

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .fact_check_agent import DynamicFactCheckAgent # 保留此行
# 請注意：此處不再需要匯入 classification_agent

# 建立 DynamicFactCheckAgent 實例，作為內部函式調用
dynamic_fact_check_instance = DynamicFactCheckAgent()


# 🎯 建立新的 Agent 類別，它將執行您的動態查核邏輯
class DynamicFactCheckWrapper(BaseAgent):
    """
    這個 Agent 負責執行動態查核邏輯，並作為一個 SequentialAgent 的步驟。
    它確保 run_async 能夠產生結果 (yield events)。
    """
    
    async def run_async(self, query: str, agent_context: CallbackContext | None = None, **kwargs):
        """
        在這個 run_async 中，我們將執行原本在 before_agent_callback 裡的邏輯。
        """
        if agent_context is None:
            return

        state = agent_context.state
        # 這裡從 state 取得 _init_session 的值，確保它已被 init_session 處理過
        news_text = state.get("_init_session", query) 
        
        if news_text:
            print("\n" + "=" * 70)
            print(">>> 檢查點：DynamicFactCheckWrapper.run_async 函式已執行！<<<")
            print("執行動態假新聞查核...")
            print("=" * 70)
            
            # 執行原本在 _before_llm_layer 裡的邏輯
            try:
                # 執行 dynamic_fact_check 的 run_async
                await dynamic_fact_check_instance.run_async(news_text, agent_context)
                
                # 結果已經自動存到 state 中了
                print("\n✅ 動態查核完成,結果已存到 state\n")
            except Exception as e:
                print(f"\n❌ 動態查核失敗: {e}\n")

        # 由於 SequentialAgent 要求子 Agent 必須產生 (yield) 事件，
        # 即使我們的主要工作是修改 state，我們也需要 yield 至少一個事件。
        # 這裡使用一個單純的 LlmAgent 來產生一個流程狀態。
        llm_wrapper_agent = LlmAgent(
            name="llm_wrapper_status",
            model="gemini-2.5-flash",
            instruction=(
                "你是 LLM 層的協調者。假新聞查核已完成並儲存到 state。\n"
                "請輸出一個簡短的確認訊息，表示動態查核流程成功。"
            ),
            output_key="llm_layer_status",
            generate_content_config=types.GenerateContentConfig(temperature=0.0),
        )

        async for event in llm_wrapper_agent.run_async(query, agent_context=agent_context, **kwargs):
            yield event


# 最終導出實例
dynamic_fact_check = DynamicFactCheckWrapper(name="dynamic_fact_check")

__all__ = [
    "dynamic_fact_check",
]