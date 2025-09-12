from typing import List
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from judge.tools import StateRecorder

# ====== Schema 定義（輸出時間軸與宣傳模式）======
class TimelineEvent(BaseModel):
    date: str = Field(description="事件發生日期（ISO 8601 或文字描述）")
    description: str = Field(description="事件概述")

class PromotionPattern(BaseModel):
    pattern: str = Field(description="宣傳或推廣模式")
    comparison: str = Field(description="與時間軸事件的比對或證據")

class HistorianOutput(BaseModel):
    timeline: List[TimelineEvent]
    promotion_patterns: List[PromotionPattern]

# ====== Historian 核心代理 ======
historian_llm_agent = LlmAgent(
    name="historian_schema_agent",
    model="gemini-2.5-flash",
    instruction=(
        "你是『歷史學者（Historian）』。\n"
        "以下提供 Curator 的整理結果 JSON：{curation}\n"
        "1) 根據資料建立重要事件時間軸。\n"
        "2) 分析是否存在宣傳或推廣模式，並給出比對結果。\n"
        "請僅輸出符合 HistorianOutput schema 的 JSON，不要額外文字。"
    ),
    output_schema=HistorianOutput,
    # 禁止向其他代理傳輸結果
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="history",
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

historian_agent = SequentialAgent(
    name="historian",
    sub_agents=[historian_llm_agent],
)


def _record_history(agent_context=None, **_):
    if agent_context is None:
        return None
    state = agent_context.state
    sr = state.get("state_record_path")
    output = state.get("history")
    try:
        from judge.tools import StateRecorder as _SR
    except Exception:
        _SR = None
    if sr and output and _SR:
        try:
            rec = _SR(sr)
            rec.record({"type": "history", "payload": output})
        except Exception:
            pass
    agents = state.setdefault("agents", {})
    agent_log = agents.setdefault("historian", {}).setdefault("log", [])
    agent_log.append({"type": "history", "payload": output})

historian_agent.after_agent_callback = _record_history
