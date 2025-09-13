from __future__ import annotations

import time
from typing import Optional, Dict, Any

import requests

# 從 config 匯入設定
from .config import (
    COFACTS_API_URL,
    COFACTS_APP_ID,
    COFACTS_APP_SECRET,
    COFACTS_API_FIRST,
    DEBUG,
)

# ---- Headers（關鍵：Accept 明確要求 JSON）----
BASE_HEADERS: Dict[str, str] = {
    "Content-Type": "application/json; charset=utf-8",
    "Accept": "application/json, application/graphql+json; charset=utf-8",
    "User-Agent": "cofacts-tool/0.1 (+https://github.com/yourrepo)",
}

def _headers() -> Dict[str, str]:
    h = dict(BASE_HEADERS)
    if COFACTS_APP_ID:
        h["x-app-id"] = COFACTS_APP_ID
    if COFACTS_APP_SECRET:
        h["x-app-secret"] = COFACTS_APP_SECRET
    return h


def _post(
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    backoff_factor: int = 2,
) -> Optional[Dict[str, Any]]:
    """
    發送 GraphQL POST 請求，附帶安全檢查與 retry/backoff。
    若非 JSON 回應（例如 GraphiQL HTML），回傳 None 並印出警告。
    """
    payload = {"query": query, "variables": variables or {}}

    for attempt in range(max_retries):
        try:
            resp = requests.post(
                COFACTS_API_URL,
                headers=_headers(),
                json=payload,
                timeout=(10, 30),  # (connect, read)
            )
            ct = resp.headers.get("content-type", "")

            if DEBUG:
                print(f"[DEBUG] status={resp.status_code} ct={ct}")

            # 只接受 JSON；有些 Gateway 會在 Accept 不正確時回 HTML（GraphiQL）
            if "application/json" not in ct.lower() and "application/graphql+json" not in ct.lower():
                if DEBUG:
                    body = resp.text[:200].replace("\n", "\\n")
                    print(f"[API WARN] Non-JSON response status={resp.status_code}, body[:200]='{body}'")
                return None

            data = resp.json()
            # GraphQL 層級錯誤處理
            if not isinstance(data, dict) or ("data" not in data and "errors" not in data):
                if DEBUG:
                    print("[API WARN] Unexpected JSON shape from GraphQL endpoint")
                return None
            return data

        except requests.RequestException as e:
            if DEBUG:
                print(f"[API ERROR] {e} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(backoff_factor ** attempt)
            else:
                return None

    return None


def list_articles(
    first: int = COFACTS_API_FIRST,
    after: Optional[str] = None,
    text: Optional[str] = None,
    time_range: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    從 Cofacts GraphQL API 取得文章列表（含 updatedAt 與 articleReplies.reply 欄位）。
    注意：pageInfo 只有 lastCursor。
    """
    query = """
    query GetArticles($first: Int, $after: String) {
      ListArticles(first: $first, after: $after) {
        edges {
          cursor
          node {
            id
            text
            createdAt
            updatedAt
            replyCount
            articleReplies {
              reply {
                id
                text
                type
                createdAt
              }
            }
          }
        }
        pageInfo {
          lastCursor
        }
      }
    }
    """

    data = _post(query, {"first": first, "after": after})
    if not data or "errors" in data:
        if DEBUG:
            errs = (data or {}).get("errors")
            if errs:
                try:
                    import json as _json
                    print(_json.dumps({"errors": errs}, ensure_ascii=False, indent=2))
                except Exception:
                    print("[API WARN] GraphQL returned errors")
            else:
                print("[API WARN] GraphQL returned no data")
        return {"edges": [], "pageInfo": {"lastCursor": None}}

    obj = (data.get("data") or {}).get("ListArticles") or {}
    edges = obj.get("edges") or []
    page_info = obj.get("pageInfo") or {}
    last_cursor = page_info.get("lastCursor")

    # ---- 本地過濾（可選）----
    filtered_edges = []
    for e in edges:
        node = (e or {}).get("node") or {}
        ok = True

        if text:
            t = (node.get("text") or "")
            if text not in t:
                ok = False

        if ok and time_range:
            created = node.get("createdAt")
            if created:
                gte = time_range.get("gte")
                lte = time_range.get("lte")
                if gte and created < gte:
                    ok = False
                if lte and created > lte:
                    ok = False

        if ok:
            filtered_edges.append(e)

    return {"edges": filtered_edges, "pageInfo": {"lastCursor": last_cursor}}




def get_article(article_id: str) -> Dict[str, Any]:
    """
    取得單篇文章資料。
    與 list_articles 的 node 欄位對齊（含 updatedAt 與 reply.createdAt）。
    回傳 dict（若失敗則回 {}）
    """
    query = """
    query GetArticle($id: String!) {
      GetArticle(id: $id) {
        id
        text
        createdAt
        updatedAt
        replyCount
        articleReplies {
          reply {
            id
            type
            text
            createdAt
          }
        }
      }
    }
    """

    data = _post(query, {"id": article_id})
    if not data or "errors" in data:
        if DEBUG:
            print(f"[API WARN] Failed to get article id={article_id}")
            # 若有 GraphQL errors 也印出來協助除錯
            errs = (data or {}).get("errors")
            if errs:
                try:
                    import json as _json
                    print(_json.dumps({"errors": errs}, ensure_ascii=False, indent=2))
                except Exception:
                    pass
        return {}

    obj = (data.get("data") or {}).get("GetArticle") or {}
    return obj if isinstance(obj, dict) else {}

