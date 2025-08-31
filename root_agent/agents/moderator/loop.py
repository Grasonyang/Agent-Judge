from google.adk.agents import LoopAgent, LlmAgent
from google.genai import types

# 統一設定停用訊號的工具
from .stop_utils import mark_stop

# 用一個小工具來「跳出」Loop（ADK 常見寫法）
def exit_loop(tool_context):
    print("Calling exit")
    tool_context.actions.escalate = True  # 告訴 LoopAgent 停止
    return {"ok": True}

# ---- 變化量計算工具 ----
def _update_metrics(state):
    """更新並寫入爭點、可信度與證據的變化量"""
    prev_points = state.get("prev_dispute_points", 0)
    curr_points = state.get("dispute_points", 0)
    state["delta_dispute_points"] = curr_points - prev_points
    state["prev_dispute_points"] = curr_points

    prev_cred = state.get("prev_credibility", 0.0)
    curr_cred = state.get("credibility", 0.0)
    state["delta_credibility"] = curr_cred - prev_cred
    state["prev_credibility"] = curr_cred

    prev_ev = state.get("prev_evidence_count", 0)
    curr_ev = len(state.get("evidence", []))
    state["new_evidence_gain"] = curr_ev - prev_ev
    state["prev_evidence_count"] = curr_ev


def _should_stop(state) -> bool:
    """判斷變化量是否觸發門檻"""
    return (
        state.get("delta_dispute_points", 0) <= 0
        or state.get("delta_credibility", 0) <= 0
        or state.get("new_evidence_gain", 0) <= 0
    )


def _metrics_before_stop(callback_context, **_):
    """在 stop_checker 執行前更新指標，並檢查是否已有停止訊號"""
    state = callback_context.state
    # 若已有人或邏輯標記要結束，直接回傳統一訊號
    if state.get("stop_signal") == "exit_loop":
        return mark_stop(state)
    _update_metrics(state)
    if _should_stop(state):
        # 標記停用訊號，統一由 stop_enforcer 處理實際退出
        return mark_stop(state)
    return None


# 檢查是否應該停止（例如輪數或無新資訊），由 LLM 產生信號並呼叫 exit_loop
stop_checker = LlmAgent(
    name="stop_checker",
    model="gemini-2.0-flash",
    instruction=(
    "根據 debate_messages 判斷是否該結束：\n"
    "規則：達到 max_turns 或連續兩輪沒有新增實質證據/新觀點。\n"
    "若該結束，請只回傳純文字 exit_loop（小寫、無標點與前後空白）；若不該結束，請回傳純文字 continue。\n"
    "注意：不要嘗試呼叫任何工具；此步僅回傳字串供後續 enforcer 處理。\n"
    "MESSAGES:\n(the current debate messages stored in state['debate_messages'])"
    ),
    output_key="stop_signal",
    before_agent_callback=_metrics_before_stop,
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
        "- 若 stop_signal 指示結束，請呼叫提供的工具 exit_loop 以結束回合；\n"
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
