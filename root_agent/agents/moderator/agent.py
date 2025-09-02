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
from root_agent.agents.social_noise.agent import social_noise_agent

# 統一由 stop_checker 呼叫退出工具
from .tools import exit_loop

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


# 工具名稱與辯論記錄欄位對應
LOG_MAP = {
    "call_advocate": ("advocate", "advocacy"),
    "call_skeptic": ("skeptic", "skepticism"),
    "call_devil": ("devil", "devil_turn"),
}


def _log_tool_output(tool, args=None, tool_context=None, tool_response=None, result=None, **_):
    """工具執行後記錄輸出

    Accept both the ADK keyword `tool_response` and older positional `result` for
    compatibility. Accept extra kwargs for forward compatibility.
    """
    # Prefer the ADK-provided keyword name 'tool_response' but fall back to
    # 'result' if present (older callers).
    response = tool_response if tool_response is not None else result
    info = LOG_MAP.get(tool.name)
    if info:
        speaker, key = info
        output = tool_context.state.get(key) if tool_context is not None else None
        if output:
            _log_turn(tool_context.state, speaker, output)
    return response


# 把子代理包成可被呼叫的工具（a2a / a3a）
advocate_tool = AgentTool(advocate_agent)
advocate_tool.name = "call_advocate"
skeptic_tool = AgentTool(skeptic_agent)
skeptic_tool.name = "call_skeptic"
devil_tool = AgentTool(devil_agent)
devil_tool.name = "call_devil"


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
        "輸入：\n- CURATION: {curation}\n- SOCIAL_NOISE: {social_noise}\n- MESSAGES(JSON array): (the current debate messages stored in state['debate_messages'])\n\n"
        "僅產生 NextTurnDecision，不呼叫任何工具。"
    ),
    # no tools
    output_schema=NextTurnDecision,
    # 禁止向父層或同儕傳遞以符合 schema 限制
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
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
    after_tool_callback=_log_tool_output,
    # no output_schema here because tools are used
    output_key="orchestrator_exec",
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
        "若決策模組 next_decision.next_speaker 為 'end'，務必呼叫提供的工具 exit_loop。\n"
        "若不該結束，請回傳純文字 continue（或回傳空字串）。\n"
        "MESSAGES:\n{debate_messages}\nNEXT_DECISION:\n{next_decision}"
    ),
    output_key="stop_signal",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# ---- referee loop (LoopAgent) ----
referee_loop = LoopAgent(
    name="debate_referee_loop",
    sub_agents=[social_noise_agent, orchestrator_agent, stop_checker],
    max_iterations=12,
)
