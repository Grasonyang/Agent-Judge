from google.adk.agents import LlmAgent

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
_utc_today   = datetime.now(timezone.utc).date().isoformat()
_local_today = datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat()

def create_disrupter_agent(output_key: str) -> LlmAgent:
    return LlmAgent(
        name="disrupter",
        model="gemini-2.5-flash",
        instruction=(
            f"今天的日期是 {_local_today}（台北時間），UTC 日期是 {_utc_today}。"
            "你是 Disrupter，注入干擾訊息來測試傳播的韌性。"
        ),
        output_key=output_key,
    )


__all__ = ["create_disrupter_agent"]

