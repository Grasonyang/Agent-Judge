"""工具模組：提供辯論紀錄、事件追蹤與檔案處理相關函式。"""

from __future__ import annotations

import asyncio
from typing import List

from google.adk.events.event import Event
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session

from ._debate_log import (
    Turn,
    load_debate_log,
    save_debate_log,
    initialize_debate_log,
    update_state_from_session,
    export_debate_log,
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


# 建立全域 InMemorySessionService
session_service = InMemorySessionService()
SESSION: Session | None = None


def create_session(state: dict | None = None) -> Session:
    """建立 Session 並設定初始 state"""

    global SESSION
    SESSION = asyncio.run(
        session_service.create_session(
            app_name="agent_judge",
            user_id="user",
            state=state
            or {
                "debate_messages": [],  # 儲存辯論訊息
                "agents": [],  # 紀錄參與代理
            },
        )
    )
    return SESSION


def get_session() -> Session:
    """取得最新 Session（含 state 與 events）"""

    if SESSION is None:
        raise RuntimeError("Session 尚未建立")
    return asyncio.run(
        session_service.get_session(
            app_name=SESSION.app_name,
            user_id=SESSION.user_id,
            session_id=SESSION.id,
        )
    )


def append_event(event: Event) -> Event:
    """同步加入事件到全域 Session 並更新指標。"""

    if SESSION is None:
        raise RuntimeError("Session 尚未建立")
    result = asyncio.run(session_service.append_event(SESSION, event))
    update_state_from_session(SESSION.state, SESSION)
    return result


def export_latest_debate_log() -> str:
    """透過 SessionService 取得最新事件並輸出辯論紀錄"""

    session = get_session()
    return export_debate_log(session)


def _before_init_session(agent_context=None, **_):
    """在 agent 執行前初始化辯論紀錄（寫入 state）。"""

    if agent_context is None:
        return None
    state = agent_context.state
    # 僅初始化辯論紀錄檔；state 變更將透過 session events 儲存
    initialize_debate_log("debate_log.json", state, reset=True)
    return None


__all__ = [
    "Turn",
    "load_debate_log",
    "save_debate_log",
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
    "create_session",
    "get_session",
    "append_event",
    "export_debate_log",
    "export_latest_debate_log",
    "_before_init_session",
]

