"""主持人代理：整合原 loop 與 stop_utils 的邏輯"""

from typing import Literal, List, Dict, Any
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from root_agent.tools import Turn, append_turn, initialize_debate_log

# 引入三方角色
from root_agent.agents.advocate.agent import advocate_agent
from root_agent.agents.skeptic.agent import skeptic_agent
from root_agent.agents.devil.agent import devil_agent

# 統一設定停用訊號的工具
from .tools import mark_stop, exit_loop, deterministic_stop_callback

# 辯論紀錄檔路徑
LOG_PATH = "debate_log.json"


def _log_turn(state: Dict[str, Any], speaker: str, output) -> None:
    """將角色輸出寫入辯論紀錄"""
    log_path = state.get("debate_log_path")
    if not log_path:
        initialize_debate_log(LOG_PATH, state, reset=True)
        log_path = state.get("debate_log_path")
    claim = getattr(output, "thesis", None) or getattr(output, "counter_thesis", None) or getattr(output, "stance", None)
    turn = Turn(
        speaker=speaker,
        content=output.model_dump_json(ensure_ascii=False),
        claim=claim,
        confidence=getattr(output, "confidence", None),
        evidence=getattr(output, "evidence", []),
    )
    append_turn(log_path, turn)


def advocate_wrapper(tool_context):
    result = advocate_agent(tool_context)
    output = tool_context.state.get("advocacy")
    if output:
        _log_turn(tool_context.state, "advocate", output)
    return result


def skeptic_wrapper(tool_context):
    result = skeptic_agent(tool_context)
    output = tool_context.state.get("skepticism")
    if output:
        _log_turn(tool_context.state, "skeptic", output)
    return result


def devil_wrapper(tool_context):
    result = devil_agent(tool_context)
    output = tool_context.state.get("devil_turn")
    if output:
        _log_turn(tool_context.state, "devil", output)
    return result


# 把子代理包成可被呼叫的工具（a2a / a3a）
advocate_tool = AgentTool(advocate_wrapper)
advocate_tool.name = "call_advocate"
skeptic_tool = AgentTool(skeptic_wrapper)
skeptic_tool.name = "call_skeptic"
devil_tool = AgentTool(devil_wrapper)
devil_tool.name = "call_devil"


def _exit_if_end(callback_context, **_):
    """若決策為 end，設定停止訊號並結束迴圈"""
    state = callback_context.state
    decision = state.get("next_decision", {})
    next_speaker = getattr(decision, "next_speaker", None)
    if next_speaker is None and isinstance(decision, dict):
        next_speaker = decision.get("next_speaker")
    if next_speaker == "end":
        # 若決策為結束，統一由工具標記停用訊號
        return mark_stop(state)
    return None

class NextTurnDecision(BaseModel):
    next_speaker: Literal["advocate", "skeptic", "devil", "end"] = Field(
        description="選擇下一位發言者；若結束，設為 'end'"
    )
    rationale: str = Field(description="為何選此人或為何結束（內部觀測用）")

# --- Step 1: decision agent (schema-only) ---
decision_agent = LlmAgent(
    name="moderator_decider",
    model="gemini-2.5-flash",
    instruction=(
        "你是主持人的決策模組。目標：在維持秩序、避免重複論點、推進爭點澄清的前提下，"
        "輸出一個 NextTurnDecision JSON（next_speaker: 'advocate'|'skeptic'|'devil'|'end'）以及簡短 rationale。\n"
        "輸入：\n- CURATION: {curation}\n- MESSAGES(JSON array): (the current debate messages stored in state['debate_messages'])\n\n"
        "僅產生 NextTurnDecision，不呼叫任何工具。"
    ),
    # no tools
    output_schema=NextTurnDecision,
    output_key="next_decision",
    # planner removed to avoid sending thinking config to model
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# --- Step 2: executor agent (tool-enabled, no output_schema) ---
executor_agent = LlmAgent(
    name="moderator_executor",
    model="gemini-2.5-flash",
    instruction=(
        "你是主持人的執行模組：讀取 state['next_decision']，若 next_speaker 為 'end' 則回傳空字串，"
        "否則呼叫相對應的工具 (call_advocate/call_skeptic/call_devil) 取得該角色的發言。"
        "工具已自動更新 state['debate_messages']，請將取得的字串原封不動地回傳。"
    ),
    tools=[advocate_tool, skeptic_tool, devil_tool],
    # no output_schema here because tools are used
    output_key="orchestrator_exec",
    # 在執行前檢查是否需要立即結束
    before_agent_callback=_exit_if_end,
    # planner removed to avoid sending thinking config to model
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# --- Combined orchestrator: decision then executor ---
orchestrator_agent = SequentialAgent(
    name="moderator_orchestrator",
    sub_agents=[decision_agent, executor_agent],
)


# ---- stop_checker (LLM) ----
stop_checker = LlmAgent(
    name="stop_checker",
    model="gemini-2.0-flash",
    tools=[exit_loop],
    instruction=(
        "根據 debate_messages 判斷是否該結束：\n"
        "規則：達到 max_turns 或連續兩輪沒有新增實質證據/新觀點。\n"
        "若該結束，請呼叫提供的工具 exit_loop 以停止迴圈；若不該結束，請回傳純文字 continue（或回傳空字串）。\n"
        "注意：只有在確定要結束時才呼叫 exit_loop 工具。\n"
        "MESSAGES:\n(the current debate messages stored in state['debate_messages'])"
    ),
    output_key="stop_signal",
    before_agent_callback=deterministic_stop_callback,
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# ---- referee loop (LoopAgent) ----
referee_loop = LoopAgent(
    name="debate_referee_loop",
    sub_agents=[orchestrator_agent, stop_checker],
    max_iterations=3,
)
