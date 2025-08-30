import sys, types, asyncio, importlib.util
from pathlib import Path

# 建立假模組以避免匯入真實的 Google ADK 與 GenAI
fake_google = types.ModuleType("google")
sys.modules.setdefault("google", fake_google)

fake_adk = types.ModuleType("google.adk")
sys.modules["google.adk"] = fake_adk
fake_agents = types.ModuleType("google.adk.agents")
fake_planners = types.ModuleType("google.adk.planners")
sys.modules["google.adk.agents"] = fake_agents
sys.modules["google.adk.planners"] = fake_planners

fake_genai = types.ModuleType("google.genai")
fake_genai_types = types.ModuleType("google.genai.types")
sys.modules["google.genai"] = fake_genai
sys.modules["google.genai.types"] = fake_genai_types
fake_genai.types = fake_genai_types

# ---- 假類別定義 ----
class BaseAgent:
    def __init__(self, name=None, sub_agents=None, output_key=None, **kwargs):
        self.name = name
        self.sub_agents = sub_agents or []
        self.output_key = output_key

    async def run_async(self, session):
        pass

class LlmAgent(BaseAgent):
    pass

class ParallelAgent(BaseAgent):
    async def run_async(self, session):
        for agent in self.sub_agents:
            await agent.run_async(session)

class SequentialAgent(BaseAgent):
    async def run_async(self, session):
        for agent in self.sub_agents:
            await agent.run_async(session)

class BuiltInPlanner:
    pass

class GenerateContentConfig:
    def __init__(self, temperature=0.0):
        self.temperature = temperature

# 將假類別註冊到模組
fake_agents.LlmAgent = LlmAgent
fake_agents.ParallelAgent = ParallelAgent
fake_agents.SequentialAgent = SequentialAgent
fake_planners.BuiltInPlanner = BuiltInPlanner
fake_genai_types.GenerateContentConfig = GenerateContentConfig

# ---- 載入原始代理程式碼 ----
ROOT = Path(__file__).resolve().parents[1]
social_spec = importlib.util.spec_from_file_location(
    "social_agent_module", ROOT / "root_agent/agents/social/agent.py"
)
social_mod = importlib.util.module_from_spec(social_spec)
social_spec.loader.exec_module(social_mod)

jury_spec = importlib.util.spec_from_file_location(
    "jury_agent_module", ROOT / "root_agent/agents/jury/agent.py"
)
jury_mod = importlib.util.module_from_spec(jury_spec)
jury_spec.loader.exec_module(jury_mod)

# 簡單的 Session 物件
class DummySession:
    def __init__(self):
        self.state = {}

# ---- 測試 ----

def test_social_agent_outputs_social_log():
    """確認社群代理會在狀態中產出 social_log。"""

    async def fake_parallel(session):
        session.state["echo_chamber"] = "EC"
        session.state["influencer"] = "INF"
        session.state["disrupter"] = "DIS"

    async def fake_aggregator(session):
        log = social_mod.SocialLog(
            echo_chamber=session.state["echo_chamber"],
            influencer=session.state["influencer"],
            disrupter=session.state["disrupter"],
            polarization_index=0.1,
            virality_score=0.2,
            manipulation_risk=0.3,
        )
        session.state["social_log"] = log.model_dump()

    social_mod._social_parallel.run_async = fake_parallel
    social_mod._social_aggregator.run_async = fake_aggregator

    session = DummySession()
    asyncio.run(social_mod.social_agent.run_async(session))
    assert "social_log" in session.state
    log = session.state["social_log"]
    # 確認新增的指標欄位存在且為浮點數
    for key in [
        "echo_chamber",
        "influencer",
        "disrupter",
        "polarization_index",
        "virality_score",
        "manipulation_risk",
    ]:
        assert key in log
    assert isinstance(log["polarization_index"], float)
    assert isinstance(log["virality_score"], float)
    assert isinstance(log["manipulation_risk"], float)


def test_jury_agent_consumes_social_log():
    """確認陪審團代理會讀取 social_log 並產出分數。"""

    async def fake_jury_run(session):
        assert "social_log" in session.state
        session.state["jury_result"] = {
            "scores": {
                "evidence_quality": 10,
                "logical_rigor": 10,
                "robustness": 10,
                "social_impact": 10,
                "total": 40,
            }
        }

    jury_mod.jury_agent.run_async = fake_jury_run

    session = DummySession()
    session.state["social_log"] = {
        "echo_chamber": "EC",
        "influencer": "INF",
        "disrupter": "DIS",
        "polarization_index": 0.1,
        "virality_score": 0.2,
        "manipulation_risk": 0.3,
    }
    asyncio.run(jury_mod.jury_agent.run_async(session))
    assert session.state["jury_result"]["scores"]["total"] == 40
