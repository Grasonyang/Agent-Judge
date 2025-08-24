from google.adk.agents import LoopAgent, LlmAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types

# 用一個小工具來「跳出」Loop（ADK 常見寫法）
def exit_loop(tool_context):
    tool_context.actions.escalate = True  # 告訴 LoopAgent 停止
    return {"ok": True}

# 檢查是否應該停止（例如輪數或無新資訊），由 LLM 產生信號並呼叫 exit_loop
stop_checker = LlmAgent(
    name="stop_checker",
    model="gemini-2.0-flash",
    instruction=(
        "根據 debate_messages 判斷是否該結束：\n"
        "規則：達到 max_turns 或連續兩輪沒有新增實質證據/新觀點時。"
        "若該結束，呼叫 exit_loop；否則輸出 'continue' 一詞（純文字即可）。\n"
        "MESSAGES:\n{debate_messages}"
    ),
    tools=[exit_loop],
    output_key="stop_signal",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(
        include_thoughts=False, thinking_budget=64
    )),
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# 匯入 orchestrator（決定誰說話＋呼叫該角色的 AgentTool）
from .orchestrator import orchestrator_agent

# 主持人回合制：每輪先決策並促成一次發言，再檢查是否該停
referee_loop = LoopAgent(
    name="debate_referee_loop",
    sub_agents=[orchestrator_agent, stop_checker],
    max_iterations=12,  # 全域護欄
)
