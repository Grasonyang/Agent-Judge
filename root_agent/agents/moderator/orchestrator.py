from typing import Literal, List, Dict, Any
from pydantic import BaseModel, Field
import json
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.planners import BuiltInPlanner
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.tools.tool_context import ToolContext
from google.adk.agents import LlmAgent as _LlmAgent
from google.genai import types as genai_types

# 辯論紀錄工具
from ..debate_log import Turn, append_turn

# 引入三方角色
from ..advocate.agent import advocate_agent
from ..skeptic.agent import skeptic_agent
from ..devil.agent import devil_agent

# 把子代理包成可被呼叫的工具（a2a / a3a）
advocate_tool = AgentTool(advocate_agent)
advocate_tool.name = "call_advocate"
skeptic_tool  = AgentTool(skeptic_agent)
skeptic_tool.name = "call_skeptic"
devil_tool    = AgentTool(devil_agent)
devil_tool.name = "call_devil"


async def _run_agent_sequence_and_return(agent_sequence: list, tool_context: ToolContext):
    """Run each agent in agent_sequence sequentially in an isolated Runner, forward state deltas, and
    if the last agent has an output_schema, parse and return it as dict; otherwise return text."""
    last_event = None
    last_agent = None
    for agent in agent_sequence:
        last_agent = agent
        runner = Runner(
            app_name=agent.name,
            agent=agent,
            artifact_service=tool_context._invocation_context.artifact_service,
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        session = await runner.session_service.create_session(
            app_name=agent.name, user_id='tmp_user', state=tool_context.state.to_dict()
        )
        # send an empty user message to trigger the agent; agents should read state
        content = genai_types.Content(role='user', parts=[genai_types.Part.from_text(text='')])
        async for event in runner.run_async(user_id=session.user_id, session_id=session.id, new_message=content):
            if event.actions.state_delta:
                tool_context.state.update(event.actions.state_delta)
            last_event = event

        # forward artifacts if any
        if runner.artifact_service:
            artifact_names = await runner.artifact_service.list_artifact_keys(
                app_name=session.app_name, user_id=session.user_id, session_id=session.id
            )
            for artifact_name in artifact_names:
                if artifact := await runner.artifact_service.load_artifact(
                    app_name=session.app_name, user_id=session.user_id, session_id=session.id, filename=artifact_name
                ):
                    await tool_context.save_artifact(filename=artifact_name, artifact=artifact)

    # Build return value from last_event
    if not last_event or not last_event.content or not last_event.content.parts:
        return ''
    # If the final agent is an LlmAgent with output_schema, validate and return dict
    if isinstance(last_agent, _LlmAgent) and getattr(last_agent, 'output_schema', None):
        merged_text = '\n'.join([p.text for p in last_event.content.parts if p.text])
        return last_agent.output_schema.model_validate_json(merged_text).model_dump(exclude_none=True)
    # otherwise return text
    return '\n'.join([p.text for p in last_event.content.parts if p.text])


async def call_advocate(args=None, tool_context: ToolContext = None):
    """呼叫正方代理，更新對話狀態並寫入辯論紀錄"""
    result = await _run_agent_sequence_and_return(
        [
            advocate_tool.agent,
            advocate_tool.agent.sub_agents[-1]
            if hasattr(advocate_tool.agent, 'sub_agents')
            else advocate_tool.agent,
        ],
        tool_context,
    )
    text = json.dumps(result, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result)
    turn = Turn(speaker="advocate", content=text)
    tool_context.state.setdefault("debate_messages", []).append(turn.model_dump())
    log_path = tool_context.state.get("debate_log_path")
    if log_path:
        append_turn(log_path, turn)
    return text


async def call_skeptic(args=None, tool_context: ToolContext = None):
    """呼叫反方代理，更新對話狀態並寫入辯論紀錄"""
    result = await _run_agent_sequence_and_return(
        [
            skeptic_tool.agent,
            skeptic_tool.agent.sub_agents[-1]
            if hasattr(skeptic_tool.agent, 'sub_agents')
            else skeptic_tool.agent,
        ],
        tool_context,
    )
    text = json.dumps(result, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result)
    turn = Turn(speaker="skeptic", content=text)
    tool_context.state.setdefault("debate_messages", []).append(turn.model_dump())
    log_path = tool_context.state.get("debate_log_path")
    if log_path:
        append_turn(log_path, turn)
    return text


async def call_devil(args=None, tool_context: ToolContext = None):
    """呼叫極端質疑者，更新對話狀態並寫入辯論紀錄"""
    result = await _run_agent_sequence_and_return(
        [
            devil_tool.agent,
            devil_tool.agent.sub_agents[-1]
            if hasattr(devil_tool.agent, 'sub_agents')
            else devil_tool.agent,
        ],
        tool_context,
    )
    text = json.dumps(result, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result)
    turn = Turn(speaker="devil", content=text)
    tool_context.state.setdefault("debate_messages", []).append(turn.model_dump())
    log_path = tool_context.state.get("debate_log_path")
    if log_path:
        append_turn(log_path, turn)
    return text

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
    # planner removed to avoid sending thinking config to model
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# --- Combined orchestrator: decision then executor ---
orchestrator_agent = SequentialAgent(
    name="moderator_orchestrator",
    sub_agents=[decision_agent, executor_agent],
)
