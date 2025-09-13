from __future__ import annotations

import asyncio
from functools import partial

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.sessions.session import Session

from judge.services.session import session_service

from judge.agents.advocate.agent import (
    advocate_agent,
    register_session as register_advocate,
)
from judge.agents.curator.agent import (
    curator_agent,
    register_session as register_curator,
)
from judge.agents.devil.agent import (
    devil_agent,
    register_session as register_devil,
)
from judge.agents.evidence.agent import (
    evidence_agent,
    register_session as register_evidence,
)
from judge.agents.historian.agent import (
    historian_agent,
    register_session as register_historian,
)
from judge.agents.jury.agent import (
    jury_agent,
    register_session as register_jury,
)
from judge.agents.moderator.agent import (
    referee_loop,
    register_session as register_moderator,
)
from judge.agents.skeptic.agent import (
    skeptic_agent,
    register_session as register_skeptic,
)
from judge.agents.social.agent import (
    social_summary_agent,
    register_session as register_social,
)
from judge.agents.social_noise.agent import (
    social_noise_agent,
    register_session as register_social_noise,
)
from judge.agents.synthesizer.agent import (
    synthesizer_agent,
    register_session as register_synthesizer,
)
from judge.tools import _before_init_session, append_event


def create_session(state: dict | None = None) -> Session:
    """建立新的 Session"""

    return asyncio.run(
        session_service.create_session(
            app_name="agent_judge",
            user_id="user",
            state=state
            or {
                "debate_messages": [],
                "agents": [],
            },
        )
    )


def bind_session(session: Session) -> None:
    """將 append_event 函式注入各代理，避免全域依賴"""

    append_event_fn = partial(append_event, session, service=session_service)
    register_curator(append_event_fn)
    register_historian(append_event_fn)
    register_social(append_event_fn)
    register_evidence(append_event_fn)
    register_jury(append_event_fn)
    register_synthesizer(append_event_fn)
    register_skeptic(append_event_fn)
    register_advocate(append_event_fn)
    register_devil(append_event_fn)
    register_social_noise(append_event_fn)
    register_moderator(append_event_fn)


# =============== Root Pipeline ===============
# 固定順序：Curator → Historian → 主持人回合制（正/反/極端）→ Social → Evidence → Jury → Synthesizer(JSON)

_init_session = LlmAgent(
    name="init_session",
    model="gemini-2.5-flash",
    instruction=("初始化 session（此代理僅用於在執行前設定 state，無需輸出）。"),
    before_agent_callback=_before_init_session,
    output_key="_init_session",
)

root_agent = SequentialAgent(
    name="root_pipeline",
    sub_agents=[
        _init_session,
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
