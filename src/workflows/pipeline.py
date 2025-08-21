"""多代理流程範例

此模組示範如何使用 `SequentialAgent` 與 `ParallelAgent` 組織
多個子代理的執行順序與並行結果整合。
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Iterable, List, Tuple

from ..agents.advocate import Advocate
from ..agents.skeptic import Skeptic
from ..agents.arbiter import Arbiter
from ..agents.curator import Curator
from ..agents.masses import Masses


class SequentialAgent:
    """簡易順序代理，依序執行多個步驟"""

    def __init__(self, steps: Iterable[Callable[[Dict[str, Any]], Dict[str, Any]]]):
        self.steps = list(steps)

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """依序將狀態傳遞給每個步驟"""
        for step in self.steps:
            state = step(state)
        return state


class ParallelAgent:
    """簡易並行代理，允許不同子代理同時執行"""

    def __init__(self, tasks: Iterable[Tuple[str, Callable[[Any], Any], str]]):
        """建立並行任務列表

        參數:
            tasks: 由三元組組成的可迭代物件，內容為
                `(輸出鍵, 代理實例, 輸入鍵)`
        """
        self.tasks = list(tasks)

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """同時執行所有子代理並整合結果"""
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(agent.run, state[input_key]): output_key
                for output_key, agent, input_key in self.tasks
            }
            return {futures[fut]: fut.result() for fut in futures}


def build_pipeline() -> SequentialAgent:
    """建立示範用的完整流程"""

    advocate = Advocate(name="advocate", model="gemini-1.5-flash")
    skeptic = Skeptic(name="skeptic", model="gemini-1.5-flash")
    arbiter = Arbiter(name="arbiter", model="gemini-1.5-flash")
    curator = Curator(name="curator", model="gemini-1.5-flash")
    masses = Masses(name="masses", model="gemini-1.5-flash")

    parallel = ParallelAgent(
        [
            ("curated", curator, "materials"),
            ("masses", masses, "question"),
        ]
    )

    def step_advocate(state: Dict[str, Any]) -> Dict[str, Any]:
        """執行倡議者"""
        state["advocate"] = advocate.run(state["proposal"])
        return state

    def step_parallel(state: Dict[str, Any]) -> Dict[str, Any]:
        """並行執行策展者與群眾"""
        state.update(parallel.run(state))
        return state

    def step_skeptic(state: Dict[str, Any]) -> Dict[str, Any]:
        """執行懷疑者"""
        state["skeptic"] = skeptic.run(state["advocate"])
        return state

    def step_arbiter(state: Dict[str, Any]) -> Dict[str, Any]:
        """綜合所有意見進行仲裁"""
        opinions: List[str] = [state["advocate"], state["skeptic"], *state["masses"]]
        state["arbiter"] = arbiter.run(opinions)
        return state

    return SequentialAgent([step_advocate, step_parallel, step_skeptic, step_arbiter])


if __name__ == "__main__":
    pipeline = build_pipeline()
    initial_state = {
        "proposal": "推廣太陽能發電",  # 初始提案
        "materials": ["太陽能成本下降", "環保效益"],  # 策展素材
        "question": "你支持推廣太陽能發電嗎？",  # 群眾問題
    }
    final_state = pipeline.run(initial_state)
    print(final_state["arbiter"])
