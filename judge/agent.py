from google.adk.agents import SequentialAgent, LlmAgent
from judge.agents import (
    curator_agent,
    historian_agent,
    social_summary_agent,
    evidence_agent,
    referee_loop,
    jury_agent,
    synthesizer_agent,
)
from judge.tools import _before_init_session, create_session

# 啟動時建立 Session，初始化 state 與事件
create_session()

# =============== Root Pipeline ===============
# 固定順序：Curator → Historian → 主持人回合制（正/反/極端）→ Social → Evidence → Jury → Synthesizer(JSON)


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
