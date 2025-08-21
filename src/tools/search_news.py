"""新聞搜尋工具"""

from __future__ import annotations

import requests
from google.adk.tools import FunctionTool


def tool(func):
    """工具裝飾器：將函式註冊為 ADK 工具"""
    return FunctionTool(func)


@tool
def search_news(keyword: str, max_results: int = 3) -> list[str]:
    """使用 Hacker News API 搜尋新聞標題"""
    url = "https://hn.algolia.com/api/v1/search"
    params = {"query": keyword}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    hits = response.json().get("hits", [])[:max_results]
    return [hit.get("title", "") for hit in hits if hit.get("title")]
