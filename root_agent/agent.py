from google.adk.agents import SequentialAgent

# === 匯入子代理 ===
from root_agent.agents import curator_agent, historian_agent
from root_agent.agents.moderator.agent import referee_loop
from root_agent.agents.social.agent import social_agent
from root_agent.agents.jury.agent import jury_agent
from root_agent.agents.synthesizer.agent import synthesizer_agent

# =============== Root Pipeline ===============
# 固定順序：Curator → Historian → 主持人回合制（正/反/極端）→ Social → Jury → Synthesizer(JSON)
root_agent = SequentialAgent(
    name="root_pipeline",
    sub_agents=[
        curator_agent,
        historian_agent,  # 歷史學者：整理時間軸與宣傳模式
        referee_loop,     # 這顆是 LoopAgent；會讀寫 state["debate_messages"]
        social_agent,
        jury_agent,
        synthesizer_agent # 產生 state["final_report_json"]
    ],
)
