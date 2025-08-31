from google.adk.agents import LoopAgent, LlmAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types

# 用一個小工具來「跳出」Loop（ADK 常見寫法）
def exit_loop(tool_context):
    print("Calling exit")
    tool_context.actions.escalate = True  # 告訴 LoopAgent 停止
    return {"ok": True}

# 檢查是否應該停止（例如輪數或無新資訊），由 LLM 產生信號並呼叫 exit_loop
stop_checker = LlmAgent(
    name="stop_checker",
    model="gemini-2.0-flash",
    instruction=(
    "根據 debate_messages 判斷是否該結束：\n"
    "規則：達到 max_turns 或連續兩輪沒有新增實質證據/新觀點時。\n"
    "若該結束，請使用提供的工具 'exit_loop' 來結束回合（必須以工具呼叫的方式發出，切勿只輸出文字 'exit_loop' 或 'exit_loop '）。\n"
    "若不該結束，請只輸出純文字 continue（不含其他標點或空白）。\n"
    "注意：模型回傳若為工具呼叫（exit_loop），系統會觸發 LoopAgent 停止；若只是輸出文字，請不要當作已經呼叫工具。\n"
    "MESSAGES:\n(the current debate messages stored in state['debate_messages'])"
    ),
    tools=[exit_loop],
    output_key="stop_signal",
    # planner removed to avoid sending thinking config to model
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# 補強：一個小的 enforcer，負責把 model 直接輸出的文字信號（例如 'exit_loop ', 'Exit', 'exit'）正規化
# 並在偵測到應該結束時以工具呼叫 exit_loop（降低模型直接輸出文字導致無法停止的機率）。
stop_enforcer = LlmAgent(
    name="stop_enforcer",
    model="gemini-2.0-flash",
    instruction=(
        "檢查 state['stop_signal'] 的內容（請先去除首尾空白並轉為小寫）：\n"
        "- 若其為 'exit_loop'、'exit' 或 'end'（或包含 'exit' 字串），請呼叫提供的工具 exit_loop 以結束回合；\n"
        "- 否則請不要呼叫任何工具，只回傳純文字 'continue'（或回傳空字串亦可）。\n"
        "CURRENT stop_signal: (the current value stored in state['stop_signal'])"
    ),
    tools=[exit_loop],
    output_key="stop_enforced",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# 匯入 orchestrator（決定誰說話＋呼叫該角色的 AgentTool）
from .orchestrator import orchestrator_agent

# 主持人回合制：每輪先決策並促成一次發言，再檢查是否該停
referee_loop = LoopAgent(
    name="debate_referee_loop",
    # run orchestrator -> stop_checker -> stop_enforcer (enforcer will call exit_loop if textual signal was emitted)
    sub_agents=[orchestrator_agent, stop_checker, stop_enforcer],
    max_iterations=3,  # 全域護欄
)
