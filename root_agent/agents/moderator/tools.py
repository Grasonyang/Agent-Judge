"""主持人相關工具：提供退出迴圈與統計指標"""

from root_agent.tools import load_debate_log


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


