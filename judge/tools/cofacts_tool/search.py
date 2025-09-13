from __future__ import annotations

import json
import math
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from .config import (
    DEFAULT_TOP_K,
    COFACTS_API_FIRST,
    COFACTS_API_CANDIDATES,
    COFACTS_HF_LOCAL_DIR,
    COFACTS_SEARCH_ENGINE,
    COFACTS_AUTO_BOOTSTRAP,
    COFACTS_AUTO_BOOTSTRAP_MODE,
    COFACTS_BOOTSTRAP_FORCE,
    DEBUG,
)
from .models import Article, SearchResult
from .hf_client import HFClient
from .api_client import list_articles as api_list_articles, get_article as api_get_article
from .index import (
    ensure_unified_cache,
    query_cached_similarity,
    has_unified_cache,
    has_index,
    bootstrap_cache_and_index,
)
from .similarity import get_engine


def _debug(msg: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {msg}")


def _normalize_time_range(time_range: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    if not time_range:
        return None
    lower = {(k or "").strip().lower(): (v or "").strip() for k, v in time_range.items() if v}
    gte = lower.get("gte") or lower.get("from")
    lte = lower.get("lte") or lower.get("to")
    out: Dict[str, str] = {}
    if gte: out["gte"] = gte
    if lte: out["lte"] = lte
    return out or None


def _within_time_range(ts: Optional[str], tr: Optional[Dict[str, str]]) -> bool:
    if not tr or not ts:
        return True
    if "gte" in tr and ts < tr["gte"]:
        return False
    if "lte" in tr and ts > tr["lte"]:
        return False
    return True


def _score_article(sim: float, article: Article) -> float:
    reply_factor = 1.0 + math.log1p(max(article.replyCount or 0, 0))
    type_counts: Dict[str, int] = {}
    for r in (article.articleReplies or []):
        t = (r.type or "").upper()
        if not t:
            continue
        type_counts[t] = type_counts.get(t, 0) + 1
    total = sum(type_counts.values()) or 1
    type_factor = 1.0 + (max(type_counts.values()) / total if type_counts else 0.0)
    return float(sim) * reply_factor * type_factor


def _page_through_api(text: str,
                      time_range: Optional[Dict[str, str]],
                      first: int,
                      total_cap: int) -> List[Dict[str, Any]]:
    """
    使用 Cofacts API 以 lastCursor 分頁抓取，直到 total_cap 或無下一頁。
    不做本地『字串包含』過濾，避免 API-only 常為 0；僅做時間範圍過濾。
    """
    after: Optional[str] = None
    acc: List[Dict[str, Any]] = []
    fetched_pages = 0
    fetched_edges = 0
    kept_edges = 0

    while len(acc) < total_cap:
        page = api_list_articles(first=first, after=after, text=None, time_range=None)
        edges = page.get("edges") or []
        fetched_pages += 1
        fetched_edges += len(edges)

        if DEBUG:
            _debug(f"api page#{fetched_pages}: edges={len(edges)} after={after!r}")

        if not edges:
            break

        for e in edges:
            node = (e or {}).get("node") or {}
            # 只保留時間條件
            if not _within_time_range(node.get("createdAt"), time_range):
                continue
            acc.append(node)
            kept_edges += 1
            if len(acc) >= total_cap:
                break

        after = (page.get("pageInfo") or {}).get("lastCursor")
        if not after:
            break

    if DEBUG:
        _debug(f"api fetched_pages={fetched_pages} fetched_edges={fetched_edges} kept={kept_edges}")
    return acc



def _load_unified_articles_jsonl() -> List[Dict[str, Any]]:
    """
    以串流方式讀取 unified/articles.jsonl 並回傳所有 rows。
    （若檔案很大，此函式仍會載入大量記憶體；建議之後搭配 ids.idx 走隨機讀取。）
    """
    udir = Path(COFACTS_HF_LOCAL_DIR or "./.hf_cache") / "unified"
    path = udir / "articles.jsonl"
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                # 略過單筆壞行，避免整體失敗
                continue
    return rows



def _scores_with_engine(query: str, docs: List[str], engine_name: Optional[str] = None) -> List[float]:
    if not docs:
        return []
    name = (engine_name or COFACTS_SEARCH_ENGINE or "tfidf").lower()
    if name == "bm25":
        eng = get_engine("bm25", corpus=docs)
        scores = eng.compute_scores(query)
    else:
        eng = get_engine(name)
        eng.fit(docs)
        scores = eng.compute_scores(query)
    return [float(x) for x in (scores.tolist() if hasattr(scores, "tolist") else list(scores))]


# ======================
# public API
# ======================

def search_text(text: str,
                top_k: int = DEFAULT_TOP_K,
                use_api: bool = True,
                use_hf: bool = True,
                time_range: Optional[Dict[str, str]] = None) -> SearchResult:
    """
    Unified search over Cofacts API and Hugging Face dataset (with local vector cache).
    自動建置：若缺 unified / index，會在首次呼叫時補齊（當 COFACTS_AUTO_BOOTSTRAP 為 True 且模式為 lazy）。
    """
    # --- 懶啟動 ---
    if COFACTS_AUTO_BOOTSTRAP and COFACTS_AUTO_BOOTSTRAP_MODE.lower() == "lazy":
        need = (not has_unified_cache()) or (not has_index())
        if need:
            _debug("search_text: auto bootstrap (lazy)")
            bootstrap_cache_and_index(force=COFACTS_BOOTSTRAP_FORCE)

    if not isinstance(top_k, int) or top_k <= 0:
        top_k = DEFAULT_TOP_K
    time_range = _normalize_time_range(time_range)

    t0 = perf_counter()
    used = {"api": False, "hf": False}
    ranked: List[Tuple[Article, float, float]] = []

    # ---- API ----
    if use_api:
        try:
            per_page = max(1, int(COFACTS_API_FIRST))
            total_cap = max(top_k * 10, int(COFACTS_API_CANDIDATES or (top_k * 50)))
            api_nodes = _page_through_api(text, time_range, per_page, total_cap)
            if api_nodes:
                used["api"] = True
                docs = [(n.get("text") or "") for n in api_nodes]
                sims = _scores_with_engine(text, docs)
                for node, sim in zip(api_nodes, sims):
                    art = Article.from_dict(node)
                    score = _score_article(sim, art)
                    ranked.append((art, float(sim), score))
        except Exception as e:
            _debug(f"API branch error: {type(e).__name__}: {e}")

    # ---- HF ----
    if use_hf:
        try:
            hits: Optional[List[Tuple[str, float]]] = None
            try:
                candidates_cap = max(1000, top_k * 200)
                hits = query_cached_similarity(text, top_n=candidates_cap)
            except Exception as e:
                _debug(f"cache query failed: {e}")
                hits = None

            ensure_unified_cache(from_hf=True, force=False)
            store = _load_unified_articles_jsonl()

            if hits:
                used["hf"] = True
                id2row = {str(r.get("id")): r for r in store}
                for aid, sim in hits:
                    row = id2row.get(str(aid))
                    if not row:
                        continue
                    if not _within_time_range(row.get("createdAt"), time_range):
                        continue
                    art = Article.from_dict(row)
                    score = _score_article(float(sim), art)
                    ranked.append((art, float(sim), score))

            if not hits:
                rows = []
                docs = []
                for r in store:
                    if not _within_time_range(r.get("createdAt"), time_range):
                        continue
                    docs.append(r.get("text") or "")
                    rows.append(r)
                if docs:
                    used["hf"] = True
                    sims = _scores_with_engine(text, docs)
                    for r, sim in zip(rows, sims):
                        art = Article.from_dict(r)
                        score = _score_article(float(sim), art)
                        ranked.append((art, float(sim), score))

        except Exception as e:
            _debug(f"HF branch error: {type(e).__name__}: {e}")

    # ---- merge / dedupe ----
    best: Dict[str, Tuple[Article, float]] = {}
    for art, _sim, sc in ranked:
        prev = best.get(art.id)
        if (not prev) or sc > prev[1]:
            best[art.id] = (art, sc)

    items = [v[0] for v in sorted(best.values(), key=lambda x: x[1], reverse=True)[:top_k]]
    _debug(f"search done in {perf_counter()-t0:.3f}s (api={used['api']} hf={used['hf']}) top_k={top_k}")
    return SearchResult(query=text, items=items, source=used)


def get_article(article_id: str) -> Optional[Article]:
    """
    Retrieve a single article by id:
    1) local unified cache
    2) HF
    3) API
    """
    # 懶啟動（確保有 unified）
    if COFACTS_AUTO_BOOTSTRAP and COFACTS_AUTO_BOOTSTRAP_MODE.lower() == "lazy":
        if not has_unified_cache():
            _debug("get_article: auto bootstrap unified (lazy)")
            bootstrap_cache_and_index(force=COFACTS_BOOTSTRAP_FORCE)

    try:
        ensure_unified_cache(from_hf=True, force=False)
        store = _load_unified_articles_jsonl()
        for r in store:
            if str(r.get("id")) == str(article_id):
                return Article.from_dict(r)
    except Exception:
        pass

    try:
        hf = HFClient()
        hf.load()
        for a in hf.joined_articles():
            if str(a.get("id")) == str(article_id):
                return Article.from_dict(a)
    except Exception:
        pass

    try:
        data = api_get_article(article_id)
        if data:
            return Article.from_dict(data)
    except Exception:
        pass
    return None
