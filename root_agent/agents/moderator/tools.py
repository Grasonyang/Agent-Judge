from google.genai import types


def mark_stop(state):
    """標記需要停用並回傳統一訊號（供 callback 使用以觸發後續處理）"""
    state["stop_signal"] = "exit_loop"
    return types.Content(parts=[types.Part.from_text(text="exit_loop")])


def exit_loop(tool_context):
    """Deterministic tool：告訴 LoopAgent 退出迴圈。

    被設為工具後，LLM 或 deterministic enforcer 可以呼叫它以觸發 loop 停止。
    """
    try:
        tool_context.actions.escalate = True
    except Exception:
        pass
    return {"ok": True}


def update_metrics(state):
    """更新並寫入爭點、可信度與證據的變化量（提取自原 loop.py）"""
    prev_points = state.get("prev_dispute_points", 0)
    curr_points = state.get("dispute_points", 0)
    state["delta_dispute_points"] = curr_points - prev_points
    state["prev_dispute_points"] = curr_points

    prev_cred = state.get("prev_credibility", 0.0)
    curr_cred = state.get("credibility", 0.0)
    state["delta_credibility"] = curr_cred - prev_cred
    state["prev_credibility"] = curr_cred

    prev_ev = state.get("prev_evidence_count", 0)
    curr_ev = len(state.get("evidence", []))
    state["new_evidence_gain"] = curr_ev - prev_ev
    state["prev_evidence_count"] = curr_ev


def should_stop(state) -> bool:
    """判斷變化量是否觸發門檻（提取自原 loop.py）"""
    return (
        state.get("delta_dispute_points", 0) <= 0
        or state.get("delta_credibility", 0) <= 0
        or state.get("new_evidence_gain", 0) <= 0
    )


def deterministic_stop_callback(callback_context, **_):
    """Deterministic callback 用於在 stop_checker 或其他 agent 執行前檢查並直接標記停止。

    如果條件達成，會呼叫 mark_stop(state) 並回傳其結果，否則回傳 None。
    """
    state = callback_context.state
    # 如果已有人或先前邏輯標記要結束，直接回傳統一訊號
    if state.get("stop_signal") == "exit_loop":
        return mark_stop(state)
    update_metrics(state)
    if should_stop(state):
        return mark_stop(state)
    return None
