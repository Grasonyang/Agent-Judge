from __future__ import annotations

from functools import partial

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.sessions.session import Session

from judge.tools.session_service import session_service

from judge.agents.moderator.advocate.agent import advocate_agent
from judge.agents.knowledge.curator import curator_agent
from judge.agents.moderator.devil.agent import devil_agent
from judge.agents.adjudication.agent import adjudication_agent
from judge.agents.adjudication.evidence import evidence_agent
from judge.agents.adjudication.jury import jury_agent
from judge.agents.adjudication.synthesizer.agent import synthesizer_agent
from judge.agents.knowledge.historian import historian_agent
from judge.agents.moderator.agent import referee_loop, executor_agent
from judge.agents.moderator.tools import log_tool_output
from judge.agents.moderator.skeptic.agent import skeptic_agent
from judge.agents.social.agent import social_summary_agent
from judge.agents.social.noise.agent import social_noise_agent
from judge.agents.llm.agent import llm_agent
from judge.agents.classifier.agent import classifier_agent
from judge.agents.weight.agent import weight_agent

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
        (curator_agent, "curator", "curation", False),
        (historian_agent, "historian", "history", False),
        (social_summary_agent, "social", "social_log", False),
        (evidence_agent, "evidence", "evidence", False),
        # 在 Web/CLI 中同時顯示美化後的 JSON
        (jury_agent, "jury", "jury_result", True),
        (synthesizer_agent, "synthesizer", "final_report_json", True),
        (advocate_agent, "advocate", "advocacy", False),
        (skeptic_agent, "skeptic", "skepticism", False),
        (devil_agent, "devil", "devil_turn", False),
        (social_noise_agent, "social_noise", "social_noise", False),
    ]

    # 迴圈設定 after_agent_callback，透過 make_record_callback 統一寫入事件
    for agent, author, key, show_pretty in agent_event_map:
        agent.after_agent_callback = partial(
            make_record_callback(author, key, show_pretty_message=show_pretty), append_event=append_event_fn
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
        adjudication_agent,
        llm_agent,
        classifier_agent,
        weight_agent
    ],
)


if __name__ == "__main__":
    session = create_session()
    bind_session(session)
    # 如需執行 root_agent，請自行呼叫對應方法
