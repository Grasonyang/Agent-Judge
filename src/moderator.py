from __future__ import annotations

from typing import Dict, List

from .agents.advocate import Advocate
from .agents.jury import Jury
from .agents.llm_agent import LlmAgent
from .agents.skeptic import Skeptic


class Moderator(LlmAgent):
    """主持人代理，用於在辯論僵持時提出引導性問題。"""

    def run(self, history: List[Dict[str, str]]) -> str:
        """生成一個引導性問題以推動辯論。"""
        history_text = "\n".join([f"{turn['speaker']}: {turn['message']}" for turn in history])
        prompt = f"""
        以下是一場辯論的對話紀錄。對話似乎陷入了僵局或重複。
        請你作為主持人，提出一個深刻、中立且具啟發性的問題，以幫助雙方從新的角度思考，並推動討論繼續進行。

        對話紀錄：
        {history_text}

        你的引導性問題：
        """
        return self.chat(prompt)


class Debate:
    """協調一場完整的辯論，從開場到裁決。"""

    def __init__(self, advocate: Advocate, skeptic: Skeptic, jury: Jury, moderator: Moderator, max_turns: int = 2) -> None:
        self.advocate = advocate
        self.skeptic = skeptic
        self.jury = jury
        self.moderator = moderator
        self.max_turns = max_turns
        self.history: List[Dict[str, str]] = []

    def _log_message(self, speaker: str, message: str) -> None:
        """記錄對話。"""
        print(f"{speaker}: {message}\n")
        self.history.append({"speaker": speaker, "message": message})

    def _check_for_stalemate(self) -> bool:
        """檢查辯論是否陷入僵局（過於簡單的實現）。"""
        if len(self.history) < 4:
            return False
        # 檢查最後幾輪的訊息是否有重複
        last_messages = [turn["message"] for turn in self.history[-4:]]
        return len(set(last_messages)) <= 2

    def _format_history_for_prompt(self) -> str:
        """將歷史紀錄格式化為單一字串。"""
        return "\n".join([f"{turn['speaker']}: {turn['message']}" for turn in self.history])

    def run(self, proposal: str) -> List[Dict[str, str]]:
        """執行完整的辯論流程，從陳述到裁決。"""
        self._log_message("Moderator", f"辯論主題：{proposal}")

        # 1. 開場陳述
        statement_pro = self.advocate.state_argument(proposal, host_prompt="請針對以下主題進行開場陳述：")
        self._log_message(self.advocate.name, statement_pro)

        statement_con = self.skeptic.state_argument(self._format_history_for_prompt(), host_prompt="針對正方的論點，請提出你的開場陳述與反對理由：")
        self._log_message(self.skeptic.name, statement_con)

        # 2. 交互詰問
        for i in range(self.max_turns):
            self._log_message("Moderator", f"--- 第 {i + 1} 輪詰問 ---")

            # 檢查是否僵局
            if self._check_for_stalemate():
                intervention = self.moderator.run(self.history)
                self._log_message(self.moderator.name, intervention)
                # 將主持人的問題加入歷史，讓下一位發言者回應
                self.history.append({"speaker": self.moderator.name, "message": intervention})

            # 正方提問 -> 反方回答
            question_pro = self.advocate.question_opponent(self._format_history_for_prompt())
            self._log_message(self.advocate.name, question_pro)

            answer_con = self.skeptic.answer_question(self._format_history_for_prompt())
            self._log_message(self.skeptic.name, answer_con)

            # 反方提問 -> 正方回答
            question_con = self.skeptic.question_opponent(self._format_history_for_prompt())
            self._log_message(self.skeptic.name, question_con)

            answer_pro = self.advocate.answer_question(self._format_history_for_prompt())
            self._log_message(self.advocate.name, answer_pro)

        # 3. 最終陳述
        self._log_message("Moderator", "--- 最終陳述 ---")
        closing_pro = self.advocate.state_argument(self._format_history_for_prompt(), host_prompt="請總結你的論點，並進行最終陳述。" )
        self._log_message(self.advocate.name, closing_pro)

        closing_con = self.skeptic.state_argument(self._format_history_for_prompt(), host_prompt="請總結你的論點，並進行最終陳述。" )
        self._log_message(self.skeptic.name, closing_con)

        # 4. 陪審團裁決
        self._log_message("Moderator", "--- 陪審團裁決 ---")
        verdict = self.jury.run([f"{turn['speaker']}: {turn['message']}" for turn in self.history])
        self._log_message(self.jury.name, verdict)

        return self.history