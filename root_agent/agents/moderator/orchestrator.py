from typing import Literal, List, Dict, Any
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import AgentTool
from google.adk.planners import BuiltInPlanner
from google.genai import types

# 引入三方角色
from ..advocate.agent import advocate_agent
from ..skeptic.agent import skeptic_agent
from ..devil.agent import devil_agent

# 把子代理包成可被呼叫的工具（a2a / a3a）
advocate_tool = AgentTool(agent=advocate_agent, name="call_advocate")
skeptic_tool  = AgentTool(agent=skeptic_agent,  name="call_skeptic")
devil_tool    = AgentTool(agent=devil_agent,    name="call_devil")

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
        "輸入：\n- CURATION: {curation}\n- MESSAGES(JSON array): {debate_messages}\n\n"
        "僅產生 NextTurnDecision，不呼叫任何工具。"
    ),
    # no tools
    output_schema=NextTurnDecision,
    output_key="next_decision",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=384)
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# --- Step 2: executor agent (tool-enabled, no output_schema) ---
executor_agent = LlmAgent(
    name="moderator_executor",
    model="gemini-2.5-flash",
    instruction=(
        "你是主持人的執行模組：讀取 state['next_decision']，若 next_speaker 為 'end' 則不呼叫任何角色，"
        "否則呼叫相對應的工具 (call_advocate/call_skeptic/call_devil) 來取得該角色的發言，"
        "將取得的發言物件（包含角色與內容）追加到 state['debate_messages']，並在 state 中記錄此次執行結果。"
    ),
    tools=[advocate_tool, skeptic_tool, devil_tool],
    # no output_schema here because tools are used
    output_key="orchestrator_exec",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=384)
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# --- Combined orchestrator: decision then executor ---
orchestrator_agent = SequentialAgent(
    name="moderator_orchestrator",
    sub_agents=[decision_agent, executor_agent],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=384)
    ),
)
