from google.adk.agents import SequentialAgent
from judge.tools import initialize_debate_log, initialize_state_record

# === 匯入子代理 ===
from judge.agents import (
    curator_agent,
    historian_agent,
    social_summary_agent,
    evidence_agent,
)
from judge.agents.moderator.agent import referee_loop
from judge.agents.jury.agent import jury_agent
from judge.agents.synthesizer.agent import synthesizer_agent

# =============== Root Pipeline ===============
# 固定順序：Curator → Historian → 主持人回合制（正/反/極端）→ Social → Evidence → Jury → Synthesizer(JSON)
from google.adk.agents import LlmAgent


# 初始化 session 的輕量 agent：使用 before_agent_callback 寫入 state
def _before_init_session(agent_context=None, **_):
    """在 agent 執行前初始化辯論紀錄（寫入 state）。

    Accepts either a callback context or no arguments (some callers invoke the
    callback without parameters)."""
    if agent_context is None:
        # no context provided; nothing to mutate
        return None
    # 確保 state 具有 debate_messages，避免模板注入階段出現 KeyError
    agent_context.state.setdefault("debate_messages", [])
    initialize_debate_log("debate_log.json", agent_context.state, reset=True)
    # 新增統一 state record 檔案，用於儲存每一步的 state 或事件（ndjson 格式）
    initialize_state_record("state_record.ndjson", agent_context.state, reset=True)


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
        social_summary_agent,
        evidence_agent,
        jury_agent,
        synthesizer_agent # 產生 state["final_report_json"]
    ],
)
