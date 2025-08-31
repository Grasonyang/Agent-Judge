from typing import Literal, List, Dict, Any
from pydantic import BaseModel, Field
import json
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

# 辯論紀錄工具
from root_agent.tools.debate_log import Turn, append_turn

# 引入三方角色
from root_agent.agents.advocate.agent import advocate_agent
from root_agent.agents.skeptic.agent import skeptic_agent
from root_agent.agents.devil.agent import devil_agent

# 把子代理包成可被呼叫的工具（a2a / a3a）
advocate_tool = AgentTool(advocate_agent)
advocate_tool.name = "call_advocate"
skeptic_tool  = AgentTool(skeptic_agent)
skeptic_tool.name = "call_skeptic"
devil_tool    = AgentTool(devil_agent)
devil_tool.name = "call_devil"


def _exit_if_end(callback_context, **_):
    """若決策為 end，設定停止訊號並結束迴圈"""
    state = callback_context.state
    decision = state.get("next_decision", {})
    next_speaker = getattr(decision, "next_speaker", None)
    if next_speaker is None and isinstance(decision, dict):
        next_speaker = decision.get("next_speaker")
    if next_speaker == "end":
        # 標記停用信號，由統一的 stop_enforcer 來觸發實際的工具呼叫
        state["stop_signal"] = "exit_loop"
        return types.Content(parts=[types.Part.from_text(text="exit_loop")])
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
