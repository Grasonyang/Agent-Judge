"""工具模組：提供辯論紀錄、事件追蹤與檔案處理相關函式。"""

from __future__ import annotations

import asyncio
from typing import Dict, List

from google.adk.events.event import Event
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session

from ._debate_log import (
    Turn,
    load_debate_log,
    save_debate_log,
    append_turn,
    initialize_debate_log,
)
from .evidence import Evidence, curator_result_to_evidence
from ._record_utils import (
    ensure_parent_dir,
    read_json_file,
    write_json_file,
    append_to_json_array,
    append_ndjson,
    read_ndjson,
)


# 建立全域 InMemorySessionService 與 Session 物件
session_service = InMemorySessionService()
SESSION: Session = session_service.create_session_sync(
    app_name="agent_judge", user_id="user"
)


def append_event(event: Event) -> Event:
    """同步加入事件到全域 Session。"""

    return asyncio.run(session_service.append_event(SESSION, event))


def session_events_to_debate_log(session: Session) -> List[Dict[str, object]]:
    """將 Session 事件轉換為辯論紀錄 JSON 陣列。"""

    log: List[Dict[str, object]] = []
    for ev in session.events:
        if ev.actions and ev.actions.state_delta:
            log.append(
                {
                    "speaker": ev.author,
                    "state_delta": ev.actions.state_delta,
                    "timestamp": ev.timestamp,
                }
            )
    return log


def _before_init_session(agent_context=None, **_):
    """在 agent 執行前初始化辯論紀錄（寫入 state）。"""

    if agent_context is None:
        return None
    state = agent_context.state
    state.setdefault("debate_messages", [])
    # 僅初始化辯論紀錄檔；state 變更將透過 session events 儲存
    initialize_debate_log("debate_log.json", state, reset=True)
    return None


__all__ = [
    "Turn",
    "load_debate_log",
    "save_debate_log",
    "append_turn",
    "initialize_debate_log",
    "ensure_parent_dir",
    "read_json_file",
    "write_json_file",
    "append_to_json_array",
    "append_ndjson",
    "read_ndjson",
    "Evidence",
    "curator_result_to_evidence",
    "SESSION",
    "append_event",
    "session_events_to_debate_log",
    "_before_init_session",
]

