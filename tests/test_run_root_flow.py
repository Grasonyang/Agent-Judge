import asyncio
from pathlib import Path
import sys
import pytest

# 加入專案根目錄至模組搜尋路徑
sys.path.append(str(Path(__file__).resolve().parents[1]))

# 匯入 run_root 函式
import root_agent.agent as root_module

# 簡單的 Session 物件，僅提供 state 字典
class DummySession:
    def __init__(self):
        self.state = {}

# 通用的 stub 代理，依照提供的 updater 來更新 state
class StubAgent:
    def __init__(self, updater=None):
        self.updater = updater or (lambda session: {})

    async def run_async(self, session):
        data = self.updater(session)
        session.state.update(data)
        return session.state

def test_run_root_full_flow(tmp_path, monkeypatch):
    """模擬完整流程並確認所有產物皆生成"""

    # ---- 建立各子代理 stub ----
    curator_agent = StubAgent(lambda s: {"curation": {"results": [{"url": "https://example.com"}]}})
    historian_agent = StubAgent(lambda s: {"history": {"events": []}})

    def moderator_step(session):
        session.state["debate_messages"].append({"speaker": "advocate", "content": "A", "topic": "X"})
        session.state["debate_messages"].append({"speaker": "skeptic", "content": "B", "topic": "X"})
        return {}
    referee_loop = StubAgent(moderator_step)

    social_agent = StubAgent(lambda s: {
        "social_log": {
            "echo_chamber": "e",
            "influencer": "i",
            "disrupter": "d",
            "polarization_index": 0.1,
            "virality_score": 0.2,
            "manipulation_risk": 0.3,
        }
    })
    jury_agent = StubAgent()
    synthesizer_agent = StubAgent(lambda s: {"final_report_json": {"title": "done"}})

    def render_stub(data):
        path = tmp_path / "report.md"
        path.write_text("ok", encoding="utf-8")
        return {"path": str(path), "bytes": b"ok"}

    # ---- 打補丁 ----
    monkeypatch.setattr(root_module, "curator_agent", curator_agent)
    monkeypatch.setattr(root_module, "historian_agent", historian_agent)
    monkeypatch.setattr(root_module, "referee_loop", referee_loop)
    monkeypatch.setattr(root_module, "social_agent", social_agent)
    monkeypatch.setattr(root_module, "jury_agent", jury_agent)
    monkeypatch.setattr(root_module, "synthesizer_agent", synthesizer_agent)
    monkeypatch.setattr(root_module, "render_final_report_md", render_stub)
    monkeypatch.setattr(root_module, "evaluate_truthfulness", lambda _: 0.9)
    monkeypatch.setattr(root_module, "evaluate_consistency", lambda _: 0.8)

    session = DummySession()
    payload = {"query": "Q", "kb_path": str(tmp_path)}

    result = asyncio.run(root_module.run_root(session, payload))

    # ---- 驗證產物 ----
    assert Path(result["final_report_path"]).exists()
    assert Path(tmp_path / "debate_log.json").exists()
    assert "social_log" in session.state
    assert session.state["evaluation"] == {"truthfulness": 0.9, "consistency": 0.8}

def test_run_root_curator_error(tmp_path, monkeypatch):
    """當 Curator 發生錯誤時應拋出異常"""

    class FailAgent:
        async def run_async(self, session):
            raise RuntimeError("curator fail")

    monkeypatch.setattr(root_module, "curator_agent", FailAgent())
    # 其餘代理設為空動作
    stub = StubAgent()
    monkeypatch.setattr(root_module, "historian_agent", stub)
    monkeypatch.setattr(root_module, "referee_loop", stub)
    monkeypatch.setattr(root_module, "social_agent", stub)
    monkeypatch.setattr(root_module, "jury_agent", stub)
    monkeypatch.setattr(root_module, "synthesizer_agent", stub)
    monkeypatch.setattr(root_module, "render_final_report_md", lambda data: {"path": str(tmp_path/"r.md"), "bytes": b""})
    monkeypatch.setattr(root_module, "evaluate_truthfulness", lambda _: 0.0)
    monkeypatch.setattr(root_module, "evaluate_consistency", lambda _: 0.0)

    session = DummySession()
    payload = {"query": "Q", "kb_path": str(tmp_path)}

    with pytest.raises(RuntimeError):
        asyncio.run(root_module.run_root(session, payload))
