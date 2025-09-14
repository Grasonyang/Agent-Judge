"""工具模組：提供辯論紀錄、事件追蹤與檔案處理相關函式。"""

from __future__ import annotations

import json

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session

from judge.tools.session_service import session_service

from .debate_log import (
    Turn,
    initialize_debate_state,
    update_state_from_session,
    append_event_update,
    export_debate_log,
    export_session,
)
from .evidence import Evidence, curator_result_to_evidence
from .file_io import ensure_parent_dir, write_json_file
from .fallacies import flatten_fallacies




async def append_event(
    session: Session,
    event: Event,
    service: InMemorySessionService = session_service,
) -> Event:
    """加入事件到指定 Session 並同步更新 state（非同步）"""

    # 透過 await 呼叫 Session 服務，避免在回呼中建立新事件迴圈
    result = await service.append_event(session, event)
    append_event_update(session.state, event)
    return result


def make_record_callback(author: str, key: str, show_pretty_message: bool = False):
    """建立統一的 after_agent_callback 以記錄代理輸出

    會從 state 中擷取資料，並透過 google.adk 的事件 API 寫入 Session。

    Args:
        author: 事件來源代理名稱
        key:    在 state 與事件中使用的鍵名
    """

    async def _callback(agent_context=None, append_event=None, **_):
        # 若未提供必要參數則不動作
        if agent_context is None or append_event is None:
            return None

        state = agent_context.state
        # 優先讀取 *_report，否則回退至原始 key
        output = state.get(f"{key}_report") or state.get(key)

        # 可選：將結構化輸出同時以 pretty JSON 作為 message 供 Web/CLI 檢視
        message: str | None = None
        if show_pretty_message and output is not None:
            try:
                if hasattr(output, "model_dump"):
                    data = output.model_dump()
                else:
                    data = output
                message = json.dumps(data, ensure_ascii=False, indent=2)
            except Exception:
                # 退回為字串
                message = str(output)

        # 非同步寫入事件，確保使用同一事件迴圈
        await append_event(
            Event(author=author, actions=EventActions(state_delta={key: output}, message=message))
        )

        return None

    return _callback


async def export_latest_debate_log(
    session: Session, service: InMemorySessionService = session_service
) -> str:
    """取得最新事件並輸出辯論紀錄（非同步）"""

    session = await service.get_session(
        app_name=session.app_name,
        user_id=session.user_id,
        session_id=session.id,
    )
    return export_debate_log(session)


async def export_latest_session(
    session: Session,
    path: str = "debate_log.json",
    service: InMemorySessionService = session_service,
) -> dict:
    """匯出最新 Session 並保存為 JSON 檔（非同步）"""

    session = await service.get_session(
        app_name=session.app_name,
        user_id=session.user_id,
        session_id=session.id,
    )
    data = export_session(session)
    write_json_file(path, data)
    return data


def _before_init_session(agent_context=None, **_):
    """在 agent 執行前初始化辯論相關的 state（無檔案耦合）。"""
    if agent_context is None:
        return None
    initialize_debate_state(agent_context.state, reset=True)
    return None


__all__ = [
    "Turn",
    "initialize_debate_state",
    "ensure_parent_dir",
    "write_json_file",
    "Evidence",
    "curator_result_to_evidence",
    "append_event",
    "update_state_from_session",
    "append_event_update",
    "make_record_callback",
    "export_debate_log",
    "export_latest_debate_log",
    "export_session",
    "export_latest_session",
    "_before_init_session",
    "flatten_fallacies",
]
