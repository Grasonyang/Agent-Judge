from google.genai import types


def mark_stop(state):
    """
    標記需要停用並回傳統一訊號（供 callback 使用以觸發後續處理）
    """
    state["stop_signal"] = "exit_loop"
    return types.Content(parts=[types.Part.from_text(text="exit_loop")])


def exit_loop(tool_context):
    """Deterministic tool：告訴 LoopAgent 退出迴圈。

    被設為工具後，LLM 或 deterministic enforcer 可以呼叫它以觸發 loop 停止。
    """
    # 使用 ADK 的 tool_context.actions.escalate 約定來通知 LoopAgent 停止
    try:
        tool_context.actions.escalate = True
    except Exception:
        # 如果 tool_context 沒有 actions 屬性，仍然回傳成功狀態以便呼叫端處理
        pass
    return {"ok": True}
