from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .search import search_text, get_article
from .models import SearchResult, Article
from .similarity import get_engine
from .config import DEFAULT_TOP_K, DEBUG, COFACTS_SEARCH_ENGINE


def _debug(msg: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {msg}")


def _dump_model(obj):
    """Return dict for Pydantic v1/v2 models."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


# -------------------------
# Tools exported to agent
# -------------------------

def cofacts_search_text(
    text: str,
    top_k: int = DEFAULT_TOP_K,
    time_range: Optional[Dict[str, str]] = None,
    use_api: bool = True,
    use_hf: bool = True,
) -> Dict[str, Any]:
    sr: SearchResult = search_text(
        text=text,
        top_k=top_k,
        time_range=time_range,
        use_api=use_api,
        use_hf=use_hf,
    )
    return _dump_model(sr)


def cofacts_get_article(article_id: str) -> Optional[Dict[str, Any]]:
    art: Optional[Article] = get_article(article_id)
    return _dump_model(art) if art else None


def cofacts_summarize_verdict(
    text: str,
    threshold: float = 0.15,
    top_k: int = DEFAULT_TOP_K,
    time_range: Optional[Dict[str, str]] = None,
    use_api: bool = True,
    use_hf: bool = True,
) -> Dict[str, Any]:
    """
    簡單的機器判讀：
    1) 先透過 search_text 拿候選文章
    2) 用 get_engine() 對候選重算相似度（支援 tfidf/bm25/sbert）
    3) 依回覆類型加總分數，超過 threshold 的取勝出類型，否則 UNSURE
    """
    sr: SearchResult = search_text(
        text=text,
        top_k=top_k,
        time_range=time_range,
        use_api=use_api,
        use_hf=use_hf,
    )

    if not sr.items:
        return {
            "query": text,
            "verdict": "UNSURE",
            "scores": {},
            "threshold": threshold,
            "evidence": [],
        }

    # 準備語料：候選文章本文
    docs = [a.text or "" for a in sr.items]
    name = (COFACTS_SEARCH_ENGINE or "tfidf").lower()

    # 依引擎正確初始化並計算相似度；失敗時回退到 tfidf
    try:
        if name == "bm25":
            eng = get_engine("bm25", corpus=docs)   # BM25 需在 init 給 corpus
            sims = eng.compute_scores(text)
        else:
            eng = get_engine(name)                  # tfidf / sbert
            eng.fit(docs)
            sims = eng.compute_scores(text)
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] verdict scoring fallback to tfidf due to {type(e).__name__}: {e}")
        eng = get_engine("tfidf")
        eng.fit(docs)
        sims = eng.compute_scores(text)

    # 依回覆類型加總分數
    scores: Dict[str, float] = {}
    for art, sim in zip(sr.items, sims):
        if not art.articleReplies:
            continue
        for r in art.articleReplies:
            t = (r.type or "").upper()
            if not t:
                continue
            scores[t] = scores.get(t, 0.0) + float(sim)

    # 閾值判定
    if not scores:
        verdict = "UNSURE"
    else:
        best_type, best_score = max(scores.items(), key=lambda x: x[1])
        total = sum(scores.values()) or 1.0
        ratio = best_score / total
        verdict = best_type if ratio >= threshold else "UNSURE"

    return {
        "query": text,
        "verdict": verdict,
        "scores": scores,
        "threshold": threshold,
        "evidence": [_dump_model(a) for a in sr.items],
    }

from .index import bootstrap_cache_and_index

def cofacts_refresh_cache(force: bool = True) -> dict:
    """
    手動刷新本地快取與索引（HF unified + TF-IDF index）
    """
    try:
        out = bootstrap_cache_and_index(force=force)
        return {"status": "ok", **out}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}



# 工具清單 (for ADK / Agent runtime)
TOOLS = [
    {
        "name": "cofacts_search_text",
        "description": "Search Cofacts by query text (API + HF).",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "top_k": {"type": "integer"},
                "time_range": {"type": "object"},
                "use_api": {"type": "boolean"},
                "use_hf": {"type": "boolean"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "cofacts_get_article",
        "description": "Get a single article by ID.",
        "parameters": {
            "type": "object",
            "properties": {"article_id": {"type": "string"}},
            "required": ["article_id"],
        },
    },
    {
        "name": "cofacts_summarize_verdict",
        "description": "Summarize verdict for a query text.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "threshold": {"type": "number"},
                "top_k": {"type": "integer"},
                "time_range": {"type": "object"},
                "use_api": {"type": "boolean"},
                "use_hf": {"type": "boolean"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "cofacts_refresh_cache",
        "description": "Refresh local HF/unified cache manually.",
        "parameters": {
            "type": "object",
            "properties": {
                "force": {"type": "boolean", "description": "Force refresh even if cache exists"},
            },
            "required": [],
        },
    },
]


#使用範例
# from judge.tools.cofacts_tool.agent_tool import (
#     cofacts_refresh_cache,
#     cofacts_search_text,
#     cofacts_summarize_verdict,
# )
# # 直接用 API client 取「純 API」資料，以便對照 unified/HF
# from judge.tools.cofacts_tool.api_client import get_article as api_get_article
# from judge.tools.cofacts_tool.search import get_article as unified_get_article

# # --------- 小工具 ---------
# def cut(s, n=120):
#     s = s or ""
#     s = s.replace("\n", " ")
#     return s[:n] + ("…" if len(s) > n else "")

# def reply_types(article):
#     types = {}
#     for r in (article.get("articleReplies") or []):
#         t = (r.get("type") or "").upper()
#         if not t and isinstance(r.get("reply"), dict):
#             t = (r["reply"].get("type") or "").upper()
#         if t:
#             types[t] = types.get(t, 0) + 1
#     return types

# def show_items(title, res, limit=3):
#     print(f"\n== {title} ==")
#     print("source flags:", res["source"])
#     print("items:", len(res["items"]))
#     for i, a in enumerate(res["items"][:limit], 1):
#         print(f"[{i}] id={a['id']}  replies={a.get('replyCount', 0)}  createdAt={a.get('createdAt')}")
#         print("    text:", cut(a.get("text")))
#         print("    types:", reply_types(a))
#         print("    url:  https://cofacts.tw/article/" + a["id"])

# from judge.tools.cofacts_tool.search import get_article as unified_get_article
# from judge.tools.cofacts_tool.api_client import get_article as api_get_article

# def to_plain(x):
#     if x is None:
#         return {}
#     if isinstance(x, dict):
#         return x
#     # pydantic v2
#     if hasattr(x, "model_dump"):
#         return x.model_dump()
#     # pydantic v1
#     if hasattr(x, "dict"):
#         return x.dict()
#     return {}

# def compare_article(aid: str):
#     print(f"\n== Compare article {aid} ==")
#     api = to_plain(api_get_article(aid))
#     uni = to_plain(unified_get_article(aid))
#     fields = ["id", "text", "createdAt", "replyCount"]
#     for f in fields:
#         v_api = api.get(f)
#         v_uni = uni.get(f)
#         same = (v_api == v_uni)
#         def cut(s, n=80):
#             s = str(s or "").replace("\n", " ")
#             return s[:n] + ("…" if len(s) > n else "")
#         print(f"{f:>10} | API={cut(v_api)}")
#         print(f"{'':>10} | UNI={cut(v_uni)}  -> {'OK' if same else 'DIFF'}")


# # --------- 先確保有快取/索引（不強制重建）---------
# print(cofacts_refresh_cache(force=False))

# query = "mRNA 疫苗"

# # HF-only
# res_hf = cofacts_search_text(query, top_k=5, use_api=False, use_hf=True)
# print(res_hf)
# show_items("HF-only", res_hf, limit=3)

# # API-only
# res_api = cofacts_search_text(query, top_k=5, use_api=True, use_hf=False)
# print(res_api)
# show_items("API-only", res_api, limit=3)



# # 對同一篇做 API vs Unified 對照（拿 HF-only 的第 1 筆）
# if res_hf["items"]:
#     first_id = res_hf["items"][0]["id"]
#     compare_article(first_id)

# # 判讀也看一下（HF-only）
# vd = cofacts_summarize_verdict("維他命C可治療新冠？", threshold=0.2, use_api=False, use_hf=True)
# print("\n== summarize_verdict (HF-only) ==")
# print("verdict:", vd["verdict"])
# print("scores:", vd.get("scores"))
# print("evidence:", len(vd.get("evidence") or []))