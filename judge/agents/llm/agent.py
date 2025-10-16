# judge/agents/llm/agent.py

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.callback_context import CallbackContext 
from google.genai import types
from google.adk.events.event_actions import EventActions # 確保匯入 EventActions

from .fact_check_agent import DynamicFactCheckAgent
dynamic_fact_check_instance = DynamicFactCheckAgent()


class DynamicFactCheckWrapper(BaseAgent):
    
    async def run_async(self, query: str, agent_context: CallbackContext | None = None, **kwargs):
        
        if agent_context is None:
            yield
            return

        # 🎯 關鍵修正 1: 立即產生一個「開始」事件，確保 SequentialAgent 識別到執行開始
        yield agent_context.event_builder(
            author=self.name, 
            message="Dynamic Fact Check Process Initiated.",
            actions=EventActions(state_delta={"llm_layer_status": "Started"})
        ).build()


        state = agent_context.state
        news_text = state.get("_init_session", query) 
        
        if news_text:
            # 這是您的檢查點，執行到這裡表示 Agent 已經在執行中
            print("\n" + "=" * 70)
            print(">>> 檢查點：DynamicFactCheckWrapper.run_async 函式已執行！<<<")
            print(f"動態查核目標: {news_text[:50]}...")
            print("=" * 70)
            
            try:
                # 🎯 執行 DynamicFactCheckAgent 的 run_async
                await dynamic_fact_check_instance.run_async(news_text, agent_context)
                
                # 🎯 關鍵修正 2: 產生一個「完成」事件，標記您的邏輯已結束
                yield agent_context.event_builder(
                    author=self.name, 
                    message="Dynamic Fact Check Logic Completed and state updated.",
                    actions=EventActions(state_delta={"llm_layer_status": "Completed"})
                ).build()
                
            except Exception as e:
                print(f"\n❌ 動態查核失敗: {e}\n")
                yield agent_context.event_builder(
                    author=self.name, 
                    message=f"Dynamic Fact Check Failed: {e}",
                    actions=EventActions(state_delta={"llm_layer_status": f"Failed: {e}"})
                ).build()
            
        else:
            yield agent_context.event_builder(author=self.name, message="Dynamic check skipped: No input text.").build()


# 最終導出實例
dynamic_fact_check = DynamicFactCheckWrapper(name="dynamic_fact_check")

__all__ = [
    "dynamic_fact_check",
]