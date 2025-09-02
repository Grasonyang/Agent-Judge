"""主持人相關工具：整合原 loop 與 stop_utils 的功能"""

from google.genai import types

from root_agent.tools import load_debate_log


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
    # 若提供辯論紀錄路徑，先載入並更新目前指標
    log_path = state.get("debate_log_path")
    if log_path:
        turns = load_debate_log(log_path)
        state["dispute_points"] = len({t.claim for t in turns if t.claim})
        confidences = [t.confidence for t in turns if t.confidence is not None]
        state["credibility"] = sum(confidences) / len(confidences) if confidences else 0.0
        state["evidence"] = [ev for t in turns for ev in t.evidence]

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
    # 若已標記結束或確實該停，標記並要求迴圈退出
    if state.get("stop_signal") == "exit_loop":
        result = mark_stop(state)
        callback_context.actions.escalate = True  # 告知 LoopAgent 停止
        return result
    update_metrics(state)
    if should_stop(state):
        result = mark_stop(state)
        callback_context.actions.escalate = True  # 告知 LoopAgent 停止
        return result
    return None

