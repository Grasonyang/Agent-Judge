from judge.tools import initialize_debate_log, initialize_state_record # 全域工具

# 初始化 session 的輕量 agent: 使用 before_agent_callback 寫入 state
def _before_init_session(agent_context=None, **_):
    """
    在 agent 執行前初始化辯論紀錄（寫入 state）。

    Accepts either a callback context or no arguments (some callers invoke the
    callback without parameters).
    """
    if agent_context is None:
        # no context provided; nothing to mutate
        return None
    # 確保 state 具有 debate_messages，避免模板注入階段出現 KeyError
    agent_context.state.setdefault("debate_messages", [])
    initialize_debate_log("debate_log.json", agent_context.state, reset=True)
    # 新增統一 state record 檔案，用於儲存每一步的 state 或事件（ndjson 格式）
    initialize_state_record("state_record.ndjson", agent_context.state, reset=True)