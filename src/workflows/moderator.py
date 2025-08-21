from __future__ import annotations

from typing import Dict, List, Protocol


class ChatAgent(Protocol):
    """簡易聊天代理介面"""

    name: str

    def chat(self, prompt: str) -> str:
        """回傳代理對提示的回覆"""
        raise NotImplementedError


class Moderator:
    """主持人：偵測重複輸出並提供新提示"""

    def __init__(
        self,
        agents: List[ChatAgent],
        max_rounds: int = 5,
        max_repeats: int = 2,
    ) -> None:
        # 儲存代理、上限與歷史紀錄
        self.agents = agents
        self.max_rounds = max_rounds
        self.max_repeats = max_repeats
        self.history: Dict[str, List[str]] = {agent.name: [] for agent in agents}

    def run(self, prompt: str) -> Dict[str, List[str]]:
        """執行對話並避免重複"""
        repeats = {agent.name: 0 for agent in self.agents}
        for _ in range(self.max_rounds):
            progress = False
            for agent in self.agents:
                prev = self.history[agent.name][-1] if self.history[agent.name] else None
                response = agent.chat(prompt)
                if response == prev:
                    repeats[agent.name] += 1
                    if repeats[agent.name] >= self.max_repeats:
                        # 達到上限直接記錄並跳過
                        self.history[agent.name].append(response)
                        continue
                    # 動態提示再試一次
                    response = agent.chat(f"請換個角度回答：{prompt}")
                    if response == prev:
                        repeats[agent.name] += 1
                        self.history[agent.name].append(response)
                        continue
                repeats[agent.name] = 0
                self.history[agent.name].append(response)
                progress = True
            if not progress:
                break
        return self.history
