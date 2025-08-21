"""Gemini LLM 客戶端封裝"""

from __future__ import annotations

import google.generativeai as genai

from .config import GEMINI_API_KEY


class LlmClient:
    """簡易的 Gemini 封裝，負責維護多輪對話"""

    def __init__(self, model: str = "gemini-pro") -> None:
        """建立模型連線並設定 API 金鑰"""
        if not GEMINI_API_KEY:
            raise ValueError("未設定 GEMINI_API_KEY 環境變數")

        # 於函式內設定金鑰，避免外洩
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel(model)
        # 使用 start_chat 以便保留對話歷史
        self._chat = self._model.start_chat(history=[])

    def generate(self, prompt: str) -> str:
        """傳送提示並取得模型回覆"""
        response = self._chat.send_message(prompt)
        return response.text or ""
