# judge/agents/llm/agent.py
"""
LLM Agent 層級: 包含動態路由的假新聞查核功能

核心設計:
- 用 Python 邏輯在 Agent 外部做路由
- 避免在 ADK sub_agents 中使用 tools
- 完全符合 Gemini 2.5 Flash 的限制
"""

from google.adk.agents import SequentialAgent
from .fact_check_agent import DynamicFactCheckAgent, classification_agent

# 建立動態路由的查核 Agent
dynamic_fact_check = DynamicFactCheckAgent()

# 建立 Sequential Agent (用於 ADK 系統)
llm_agent = SequentialAgent(
    name="llm_layer",
    sub_agents=[
        classification_agent,  # 只放純 LLM 的分類 agent
    ],
)