"""
Moderator orchestrator: 三輪辯論流程
第一輪：Advocate 論述 -> Skeptic 論述
第二輪：Advocate 質疑 -> Skeptic 回應 -> Skeptic 質疑 -> Advocate 回應
第三輪：Advocate 總結 -> Skeptic 總結
"""
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
from google.genai import types
from .skeptic1.agent import skeptic_agent1
from .skeptic2.agent import skeptic_agent2
from .skeptic3.agent import skeptic_agent3
from .skeptic4.agent import skeptic_agent4
from .advocate1.agent import advocate_agent1
from .advocate2.agent import advocate_agent2    
from .advocate3.agent import advocate_agent3
from .advocate4.agent import advocate_agent4
from .advocate.agent import advocate_agent
from .skeptic.agent import skeptic_agent

from .tools import (
    exit_loop,
    ensure_debate_messages,
    advocate_tool,
    skeptic_tool,
    devil_tool,
    NextTurnDecision,
)
from judge.agents.social.noise.agent import social_noise_agent


# --- Step 1: decision agent (schema-only) ---
decision_agent = LlmAgent(
    name="moderator_decider",
    model="gemini-2.0-flash",
    instruction=(
        "你是主持人的決策模組。目標：在維持秩序、避免重複論點、推進爭點澄清的前提下，"
        "依照輸入的內容，去釐清爭議點，並決定下一步由哪個角色發言（advocate/skeptic/devil），已無爭議點時請輸出end"
        "角色說明：\n - Advocate：支持主張的一方，負責提出論點與證據。\n - Skeptic：質疑主張的一方，負責挑戰論點並提出反證。\n - Devil's Advocate：扮演極端質疑角色，對正反方的論點提出極端的意見，以促進辯論深入。\n\n"
        "輸出一個 NextTurnDecision JSON（next_speaker: 'advocate'|'skeptic'|'devil'|'end'）以及簡短 rationale。\n"
        "輸入：\n- CURATION: {curation}\n- SOCIAL_NOISE: {social_noise}\n- MESSAGES(JSON array): (the current debate messages stored in state['debate_messages'])\n- advocate初始論述:state['advocacy1']\n skeptic初始論述:state['skepticism1']\n\n"
        "僅產生 NextTurnDecision，不呼叫任何工具。"
    ),
    before_agent_callback=ensure_debate_messages,
    output_schema=NextTurnDecision,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="next_decision",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json"
    ),
)


# --- Step 2: executor agent (tool-enabled, no output_schema) ---
executor_agent = LlmAgent(
    name="moderator_executor",
    model="gemini-2.0-flash",
    instruction=(
        "你是主持人的執行模組：讀取 state['next_decision']，若 next_speaker 為 'end' 則回傳空字串，"
        "否則呼叫相對應的工具 (call_advocate/call_skeptic/call_devil) 取得該角色的發言。"
        "工具已自動更新 state['debate_messages']，請將取得的字串原封不動地回傳。"
    ),
    before_agent_callback=ensure_debate_messages,
    tools=[advocate_tool, skeptic_tool, devil_tool],
    after_tool_callback=None,
    output_key="orchestrator_exec",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="text/plain"
    ),
)

orchestrator_agent = SequentialAgent(
    name="moderator_orchestrator",
    sub_agents=[decision_agent, executor_agent],
)


stop_checker = LlmAgent(
    name="stop_checker",
    model="gemini-2.5-flash",
    tools=[exit_loop],
    instruction=(
        "根據 debate_messages 判斷是否該結束：\n"
        "規則：達到 max_turns 或連續兩輪沒有新增實質證據/新觀點。\n"
        "若決策模組 next_decision.next_speaker 為 'end'，務必呼叫提供的工具 exit_loop。\n"
        "若不該結束，請回傳純文字 continue（或回傳空字串）。\n"
        "MESSAGES:\n(the current debate messages are available in state['debate_messages'])\n"
        "NEXT_DECISION:\n(the current moderator decision is available in state['next_decision'])"
    ),
    before_agent_callback=ensure_debate_messages,
    output_key="stop_signal",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="text/plain"
    ),
)

referee_loop = LoopAgent(
    name="debate_referee_loop",
    sub_agents=[orchestrator_agent, stop_checker],
    max_iterations=3,
)

debate3_agent = SequentialAgent(
    name="moderator_orchestrator",
    sub_agents=[social_noise_agent,advocate_agent1, skeptic_agent1,referee_loop],
)