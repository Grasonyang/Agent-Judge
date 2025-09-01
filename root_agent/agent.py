from google.adk.agents import SequentialAgent

from root_agent.tools import initialize_debate_log

# === 匯入子代理 ===
from root_agent.agents import curator_agent, historian_agent
from root_agent.agents.moderator.agent import referee_loop
from root_agent.agents.social.agent import social_agent
from root_agent.agents.jury.agent import jury_agent
from root_agent.agents.synthesizer.agent import synthesizer_agent

# =============== Root Pipeline ===============
# 固定順序：Curator → Historian → 主持人回合制（正/反/極端）→ Social → Jury → Synthesizer(JSON)
from google.adk.agents import LlmAgent


# 初始化 session 的輕量 agent：使用 before_agent_callback 寫入 state
def _before_init_session(agent_context=None, **_):
    """在 agent 執行前初始化辯論紀錄（寫入 state）。

    Accepts either a callback context or no arguments (some callers invoke the
    callback without parameters)."""
    if agent_context is None:
        # no context provided; nothing to mutate
        return None
    initialize_debate_log("debate_log.json", agent_context.state, reset=True)


_init_session = LlmAgent(
    name="init_session",
    model="gemini-2.5-flash",
    instruction=("初始化 session（此代理僅用於在執行前設定 state，無需輸出）。"),
    # 不實際呼叫 tools 或產生 schema，僅利用 before_agent_callback
    before_agent_callback=_before_init_session,
    output_key="_init_session",
)


root_agent = SequentialAgent(
    name="root_pipeline",
    sub_agents=[
        _init_session,    # 初始化辯論紀錄檔
        curator_agent,
        historian_agent,  # 歷史學者：整理時間軸與宣傳模式
        referee_loop,     # 這顆是 LoopAgent；會讀寫 state["debate_messages"]
        social_agent,
        jury_agent,
        synthesizer_agent # 產生 state["final_report_json"]
    ],
)
