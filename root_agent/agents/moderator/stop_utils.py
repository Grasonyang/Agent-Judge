from google.genai import types


def mark_stop(state):
    """標記需要停止並回傳統一訊號"""
    state["stop_signal"] = "exit_loop"
    return types.Content(parts=[types.Part.from_text(text="exit_loop")])
