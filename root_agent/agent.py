from typing import Optional
from pydantic import BaseModel, Field

from google.adk.agents import SequentialAgent
from google.genai import types
from google.adk.planners import BuiltInPlanner

# 知識庫 API
from .knowledge_base import save_graphlet, load_graphlet

# === 匯入子代理 ===
from .agents import curator_agent, historian_agent
from .agents.moderator.loop import referee_loop          # LoopAgent（主持人回合制）
from .agents.social.agent import social_agent
from .agents.jury.agent import jury_agent
from .agents.synthesizer.agent import synthesizer_agent
from .agents.synthesizer import render_final_report_md   # 工具：JSON → Markdown

# =============== Root 入口參數 / 輸出 ===============
class RootInput(BaseModel):
    # 交給 Curator 的查詢
    query: str = Field(description="要調查/辯論的主題或關鍵字")
    top_k: int = Field(default=5, description="Curator 搜尋回傳前幾筆結果（1~10）")
    site: Optional[str] = Field(default=None, description="可選：限制站點（不含 'site:' 前綴），例如 'reuters.com'")

    # 主持人/對話控制
    enable_devil: bool = Field(default=True, description="是否啟用極端質疑者參與回合")
    max_turns: int = Field(default=12, description="主持人回合上限（LoopAgent 的護欄）")

    # 產物
    emit_markdown: bool = Field(default=True, description="是否將最終 JSON 報告輸出為 Markdown 檔")

class RootOutput(BaseModel):
    final_report_path: Optional[str] = Field(default=None, description="輸出 Markdown 檔案路徑（若有）")

# =============== Root Pipeline ===============
# 固定順序：Curator → Historian → 主持人回合制（正/反/極端）→ Social → Jury → Synthesizer(JSON)
root_agent = SequentialAgent(
    name="root_pipeline",
    sub_agents=[
        curator_agent,
        historian_agent,  # 歷史學者：整理時間軸與宣傳模式
        referee_loop,     # 這顆是 LoopAgent；會讀寫 state["debate_messages"]
        social_agent,
        jury_agent,
        synthesizer_agent # 產生 state["final_report_json"]
    ],
)

# =============== 便捷執行函式（應用層呼叫） ===============
async def run_root(session, payload: dict) -> dict:
    """
    用法：
        result_state = await run_root(session, {
            "query": "台積電 CoWoS 產能",
            "top_k": 5,
            "enable_devil": True,
            "max_turns": 10,
            "emit_markdown": True
        })
    """
    # ---- 初始化 state（上游輸入）----
    # Curator 需要的輸入
    session.state.update({
        "query": payload.get("query", ""),
        "top_k": payload.get("top_k", 5),
        "site": payload.get("site"),
    })

    # 主持人回合需要的控制旗標與對話容器
    session.state.setdefault("debate_messages", [])
    session.state["enable_devil"] = bool(payload.get("enable_devil", True))
    # 若你在 referee_loop/或 orchestrator 內有使用 max_iterations，可在那裡讀 state["max_turns"]
    session.state["max_turns"] = int(payload.get("max_turns", 12))

    # 知識庫路徑（預設存於當前資料夾的 kb/）
    kb_path = payload.get("kb_path", "kb")
    session.state["kb_path"] = kb_path

    # ---- 逐步執行管線並與 KB 互動 ----
    # 1) Curator：搜尋整理並寫入 KB
    result_state = await curator_agent.run_async(session)
    if result_state.get("curation"):
        save_graphlet("curation", result_state["curation"], kb_path)

    # 2) Historian：分析時間軸並寫入 KB
    result_state = await historian_agent.run_async(session)
    if result_state.get("history"):
        save_graphlet("history", result_state["history"], kb_path)

    # 3) Moderator：先從 KB 讀取必要資料
    for key in ("curation", "history"):
        try:
            session.state[key] = load_graphlet(key, kb_path)
        except FileNotFoundError:
            pass
    result_state = await referee_loop.run_async(session)

    # 4) Social Agent：再次確認從 KB 讀取
    for key in ("curation", "history"):
        try:
            session.state[key] = load_graphlet(key, kb_path)
        except FileNotFoundError:
            pass
    result_state = await social_agent.run_async(session)

    # 5) Jury 與 6) Synthesizer
    result_state = await jury_agent.run_async(session)
    result_state = await synthesizer_agent.run_async(session)

    # ---- 依需求輸出 Markdown ----
    final_path = None
    if payload.get("emit_markdown", True):
        fr_json = result_state.get("final_report_json")
        if fr_json:
            out = render_final_report_md(fr_json)   # {"path": "...", "bytes": ...}
            final_path = out["path"]
            result_state["final_report_path"] = final_path

    return result_state
