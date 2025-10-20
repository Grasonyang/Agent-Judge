# judge/agent.py

from __future__ import annotations

from functools import partial

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.sessions.session import Session
from google.genai import types

from judge.tools.session_service import session_service
from judge.agents.llm.agent import llm_agent  # ✅ 修正: 正確導入

from judge.agents.knowledge.curator import curator_agent
from judge.agents.moderator.devil.agent import devil_agent
from judge.agents.adjudication.agent import adjudication_agent
from judge.agents.adjudication.evidence import evidence_agent
from judge.agents.adjudication.jury import jury_agent
from judge.agents.adjudication.synthesizer.agent import synthesizer_agent
from judge.agents.knowledge.historian import historian_agent
from judge.agents.moderator.agent import orchestrator_agent
from judge.agents.moderator.tools import log_tool_output

from judge.agents.social.agent import social_summary_agent
from judge.agents.social.noise.agent import social_noise_agent

from judge.agents.classifier.agent import classifier_agent
from judge.agents.weight.agent import weight_agent
from judge.agents.debatelog.agent import debate_agent
from judge.tools import _before_init_session, append_event, make_record_callback


def create_session(state: dict | None = None) -> Session:
    """建立新的 Session（同步呼叫版）"""
    default_state = {
        "debate_messages": [],
        "agents": [],
        "debate_turn": 0,
        "current_round": 1,
        "current_phase": "statement",
    }
    
    if state:
        default_state.update(state)

    return session_service.create_session_sync(
        app_name="agent_judge",
        user_id="user",
        state=default_state,
    )


def bind_session(session: Session) -> None:
    """將 append_event 函式注入各代理"""

    append_event_fn = partial(append_event, session, service=session_service)

    agent_event_map = [
        (curator_agent, "curator", "curation", False),
        (historian_agent, "historian", "history", False),
        (social_summary_agent, "social", "social_log", False),
        (evidence_agent, "evidence", "evidence", False),
        (jury_agent, "jury", "jury_result", True),
        (synthesizer_agent, "synthesizer", "final_report_json", True),
        (social_noise_agent, "social_noise", "social_noise", False),
    ]

    for agent, author, key, show_pretty in agent_event_map:
        agent.after_agent_callback = partial(
            make_record_callback(author, key, show_pretty_message=show_pretty),
            append_event=append_event_fn
        )


# ========== Root Pipeline ==========
init_session = LlmAgent(
    name="init_session",
    model="gemini-2.0-flash",
    instruction=(
        "初始化 session。"
        "請把接收到的資訊做提煉，使輸入文本僅保留事實的描述及事情發生的時間，移除個人意見內容，限200字內。"
        "注意切勿自行修改文本內容，請真實以輸入文本內容作呈現。"
        "將結果存入 state['_init_session'] 中。"
    ),
    before_agent_callback=_before_init_session,
    output_key="_init_session",
)


# ✅ 修正: 使用正確初始化的 dynamic_fact_check
root_agent = SequentialAgent(
    name="root_pipeline",
    sub_agents=[
        init_session,
        curator_agent,
        historian_agent,
        orchestrator_agent,
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