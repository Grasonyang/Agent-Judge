"""
Cofacts Tool
"""
from __future__ import annotations

from .config import DEBUG, COFACTS_AUTO_BOOTSTRAP, COFACTS_AUTO_BOOTSTRAP_MODE, COFACTS_BOOTSTRAP_FORCE
from .search import search_text, get_article
from .models import Reply, Article, SearchResult
from .agent_tool import (
    TOOLS,
    cofacts_search_text,
    cofacts_get_article,
    cofacts_summarize_verdict,
)
# 若你也有 refresh_cache 工具函式，就一併導出

# eager bootstrap
if COFACTS_AUTO_BOOTSTRAP and str(COFACTS_AUTO_BOOTSTRAP_MODE).lower() == "eager":
    try:
        from .index import bootstrap_cache_and_index
        bootstrap_cache_and_index(force=COFACTS_BOOTSTRAP_FORCE)
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] eager bootstrap failed: {e}")

__all__ = [
    "Reply", "Article", "SearchResult",
    "search_text", "get_article",
    "TOOLS",
    "cofacts_search_text", "cofacts_get_article", "cofacts_summarize_verdict",
]

if DEBUG:
    print("[DEBUG] cofacts_tool package imported")
