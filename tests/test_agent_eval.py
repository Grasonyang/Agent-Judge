"""使用 ADK 評估框架驗證回應與工具軌跡"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("GEMINI_API_KEY", "dummy")
sys.path.append(str(Path(__file__).resolve().parents[1]))

from google.adk.evaluation.final_response_match_v1 import RougeEvaluator
from google.adk.evaluation.trajectory_evaluator import TrajectoryEvaluator
from google.adk.evaluation.eval_case import Invocation, IntermediateData
from google.adk.evaluation.eval_metrics import EvalMetric, PrebuiltMetrics
from google.genai.types import Content, FunctionCall, Part

from src.agents.llm_agent import LlmAgent
from google.adk.tools import FunctionTool


class _DummyLlm:
    """回傳固定字串的假 LLM"""

    def generate(self, prompt: str) -> str:
        return "測試回應"


def _fake_search_news(keyword: str, max_results: int = 3) -> list[str]:
    """不發出網路請求的假新聞搜尋工具"""
    return [f"{keyword} 新聞"]


class _TestAgent(LlmAgent):
    """使用假 LLM 與工具的測試代理"""

    def __init__(self) -> None:
        tool = FunctionTool(_fake_search_news)
        super().__init__(name="tester", tools=[tool])
        self._llm = _DummyLlm()


def test_response_and_tool_trajectory() -> None:
    """驗證代理回應與工具軌跡"""
    agent = _TestAgent()
    query = "AI"

    # 執行工具並紀錄
    news = _fake_search_news(query)
    agent.tool_logs.append({"name": "search_news", "input": {"keyword": query}, "output": news})

    # 產生回應
    reply = agent.chat(f"請根據以下新聞提供摘要：{news}")
    assert reply == "測試回應"

    # 將紀錄轉為 Invocation 以供評估
    actual_call = FunctionCall(name=agent.tool_logs[0]["name"], args=agent.tool_logs[0]["input"])
    actual = Invocation(
        invocation_id="1",
        user_content=Content(role="user", parts=[Part(text=query)]),
        final_response=Content(role="model", parts=[Part(text=reply)]),
        intermediate_data=IntermediateData(tool_uses=[actual_call]),
    )

    expected_call = FunctionCall(name="search_news", args={"keyword": query})
    expected = Invocation(
        invocation_id="1",
        user_content=Content(role="user", parts=[Part(text=query)]),
        final_response=Content(role="model", parts=[Part(text="測試回應")]),
        intermediate_data=IntermediateData(tool_uses=[expected_call]),
    )

    # 使用 ROUGE 評估回應是否符合預期
    rouge = RougeEvaluator(EvalMetric(metric_name=PrebuiltMetrics.RESPONSE_MATCH_SCORE.value, threshold=0.0))
    result = rouge.evaluate_invocations([actual], [expected])
    assert result.overall_eval_status.name == "PASSED"

    # 評估工具軌跡是否一致
    traj = TrajectoryEvaluator(threshold=1.0)
    t_result = traj.evaluate_invocations([actual], [expected])
    assert t_result.overall_eval_status.name == "PASSED"
