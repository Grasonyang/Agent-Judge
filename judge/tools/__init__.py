"""工具模組：提供辯論紀錄、事件追蹤與檔案處理相關函式。"""

from __future__ import annotations

import asyncio
from typing import List

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session

from ._debate_log import (
    Turn,
    load_debate_log,
    save_debate_log,
    initialize_debate_log,
    update_state_from_session,
    export_debate_log,
    export_session,
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


# 建立全域 InMemorySessionService（可依需求替換為其他實作）
session_service = InMemorySessionService()


def append_event(session: Session, event: Event, service: InMemorySessionService = session_service) -> Event:
    """加入事件到指定 Session 並同步更新 state"""

    result = asyncio.run(service.append_event(session, event))
    update_state_from_session(session.state, session)
    return result


def make_record_callback(author: str, key: str):
    """建立統一的 after_agent_callback 以記錄代理輸出

    會從 state 中擷取資料，並透過 google.adk 的事件 API 寫入 Session。

    Args:
        author: 事件來源代理名稱
        key:    在 state 與事件中使用的鍵名
    """

    def _callback(agent_context=None, append_event=None, **_):
        # 若未提供必要參數則不動作
        if agent_context is None or append_event is None:
            return None

        state = agent_context.state
        # 優先讀取 *_report，否則回退至原始 key
        output = state.get(f"{key}_report") or state.get(key)

        append_event(
            Event(author=author, actions=EventActions(state_delta={key: output}))
        )

        return None

    return _callback


def export_latest_debate_log(session: Session, service: InMemorySessionService = session_service) -> str:
    """取得最新事件並輸出辯論紀錄"""

    session = asyncio.run(
        service.get_session(
            app_name=session.app_name,
            user_id=session.user_id,
            session_id=session.id,
        )
    )
    return export_debate_log(session)


def export_latest_session(
    session: Session, path: str = "debate_log.json", service: InMemorySessionService = session_service
) -> dict:
    """匯出最新 Session 並保存為 JSON 檔"""

    session = asyncio.run(
        service.get_session(
            app_name=session.app_name,
            user_id=session.user_id,
            session_id=session.id,
        )
    )
    data = export_session(session)
    write_json_file(path, data)
    return data


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
    "append_event",
    "make_record_callback",
    "export_debate_log",
    "export_latest_debate_log",
    "export_session",
    "export_latest_session",
    "_before_init_session",
]

