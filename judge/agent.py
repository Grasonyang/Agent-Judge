from __future__ import annotations

from functools import partial

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.sessions.session import Session

from judge.tools.session_service import session_service

from judge.agents.debate.moderator.debaters.advocate.agent import advocate_agent
from judge.agents.knowledge.curator import curator_agent
from judge.agents.debate.moderator.debaters.devil.agent import devil_agent
from judge.agents.adjudication.evidence import evidence_agent
from judge.agents.knowledge.historian import historian_agent
from judge.agents.adjudication.jury import jury_agent
from judge.agents.debate.moderator.agent import referee_loop, executor_agent
from judge.agents.debate.moderator.tools import log_tool_output
from judge.agents.debate.moderator.debaters.skeptic.agent import skeptic_agent
from judge.agents.social.agent import social_summary_agent
from judge.agents.social_noise.agent import social_noise_agent
from judge.agents.adjudication.synthesizer import synthesizer_agent

from judge.tools import _before_init_session, append_event, make_record_callback


def create_session(state: dict | None = None) -> Session:
    """建立新的 Session（同步呼叫版）"""

    # 使用 google.adk 提供的同步 API，避免在此處建立事件迴圈
    return session_service.create_session_sync(
        app_name="agent_judge",
        user_id="user",
        state=state
        or {
            "debate_messages": [],
            "agents": [],
        },
    )


def bind_session(session: Session) -> None:
    """將 append_event 函式注入各代理，避免全域依賴"""

    append_event_fn = partial(append_event, session, service=session_service)

    # 統一列出需要寫入事件的代理與對應鍵值
    agent_event_map = [
        (curator_agent, "curator", "curation"),
        (historian_agent, "historian", "history"),
        (social_summary_agent, "social", "social_log"),
        (evidence_agent, "evidence", "evidence"),
        (jury_agent, "jury", "jury_result"),
        (synthesizer_agent, "synthesizer", "final_report_json"),
        (advocate_agent, "advocate", "advocacy"),
        (skeptic_agent, "skeptic", "skepticism"),
        (devil_agent, "devil", "devil_turn"),
        (social_noise_agent, "social_noise", "social_noise"),
    ]

    # 迴圈設定 after_agent_callback，透過 make_record_callback 統一寫入事件
    for agent, author, key in agent_event_map:
        agent.after_agent_callback = partial(
            make_record_callback(author, key), append_event=append_event_fn
        )

    # 主持人執行器需額外紀錄工具輸出
    executor_agent.after_tool_callback = partial(
        log_tool_output, append_event=append_event_fn
    )


# =============== Root Pipeline ===============
# 固定順序：Curator → Historian → 主持人回合制（正/反/極端）→ Social → Evidence → Jury → Synthesizer(JSON)

init_session = LlmAgent(
    name="init_session",
    model="gemini-2.5-flash",
    instruction=("初始化 session（此代理僅用於在執行前設定 state，無需輸出）。"),
    before_agent_callback=_before_init_session,
    output_key="_init_session",
)

root_agent = SequentialAgent(
    name="root_pipeline",
    sub_agents=[
        init_session,
        curator_agent,
        historian_agent,
        referee_loop,
        social_summary_agent,
        evidence_agent,
        jury_agent,
        synthesizer_agent,
    ],
)


if __name__ == "__main__":
    session = create_session()
    bind_session(session)
    # 如需執行 root_agent，請自行呼叫對應方法
