# 📖 Cofacts 查詢工具 (Agent-Judge plugin)

這個工具整合 **Cofacts API** 與 **Hugging Face Dataset Cache**，提供即時或離線的事實查核文章搜尋與判斷功能。
適用於 **Agent-Judge 架構** 或獨立使用。

---

## ✨ 功能特色

1. **雙模式查詢**

   * `use_api=True` → 即時查詢 Cofacts GraphQL API
   * `use_hf=True` → 使用 Hugging Face 緩存資料集 (離線可用)

2. **統一緩存 (unified cache)**

   * 將 `articles` / `replies` / `article_replies` 合併為單一 JSONL
   * 本地 `.vector_cache/` 自動建立索引 (TF-IDF / BM25)

3. **相似度搜尋**

   * 支援 `tfidf`、`bm25` 引擎
   * 可根據文字內容搜尋最相近的 Cofacts 文章

4. **自動判讀 (summarize verdict)(只是單純統計，沒有AI)**

   * 統計候選文章的回覆標籤
   * 輸出簡單判斷結果：

     * `RUMOR`：謠言
     * `NOT_RUMOR`：非謠言
     * `NOT_ARTICLE`：無法判定
     * `UNSURE`：不確定

---

## ⚙️ 安裝與設定

```bash
git clone https://github.com/你的帳號/Agent-Judge.git
cd Agent-Judge/89-cofact查詢工具/Agent-Judge
pip install -r requirements.txt
```

環境變數 (可選)：

如果要連接hugging face資料，HF_TOKEN一定要設

```bash
export COFACTS_API_URL="https://api.cofacts.tw/graphql"
export COFACTS_APP_ID=""
export COFACTS_APP_SECRET=""
```

---

## 🖥️ 使用範例

```python
#可根據文字內容搜尋最相近的 Cofacts 文章
from judge.tools.cofacts_tool.agent_tool import (
    cofacts_refresh_cache,
    cofacts_search_text,
    cofacts_summarize_verdict,
)
# 直接用 API client 取「純 API」資料，以便對照 unified/HF
from judge.tools.cofacts_tool.api_client import get_article as api_get_article
from judge.tools.cofacts_tool.search import get_article as unified_get_article

# --------- 小工具 ---------
def cut(s, n=120):
    s = s or ""
    s = s.replace("\n", " ")
    return s[:n] + ("…" if len(s) > n else "")

def reply_types(article):
    types = {}
    for r in (article.get("articleReplies") or []):
        t = (r.get("type") or "").upper()
        if not t and isinstance(r.get("reply"), dict):
            t = (r["reply"].get("type") or "").upper()
        if t:
            types[t] = types.get(t, 0) + 1
    return types

def show_items(title, res, limit=3):
    print(f"\n== {title} ==")
    print("source flags:", res["source"])
    print("items:", len(res["items"]))
    for i, a in enumerate(res["items"][:limit], 1):
        print(f"[{i}] id={a['id']}  replies={a.get('replyCount', 0)}  createdAt={a.get('createdAt')}")
        print("    text:", cut(a.get("text")))
        print("    types:", reply_types(a))
        print("    url:  https://cofacts.tw/article/" + a["id"])

from judge.tools.cofacts_tool.search import get_article as unified_get_article
from judge.tools.cofacts_tool.api_client import get_article as api_get_article

def to_plain(x):
    if x is None:
        return {}
    if isinstance(x, dict):
        return x
    # pydantic v2
    if hasattr(x, "model_dump"):
        return x.model_dump()
    # pydantic v1
    if hasattr(x, "dict"):
        return x.dict()
    return {}

def compare_article(aid: str):
    print(f"\n== Compare article {aid} ==")
    api = to_plain(api_get_article(aid))
    uni = to_plain(unified_get_article(aid))
    fields = ["id", "text", "createdAt", "replyCount"]
    for f in fields:
        v_api = api.get(f)
        v_uni = uni.get(f)
        same = (v_api == v_uni)
        def cut(s, n=80):
            s = str(s or "").replace("\n", " ")
            return s[:n] + ("…" if len(s) > n else "")
        print(f"{f:>10} | API={cut(v_api)}")
        print(f"{'':>10} | UNI={cut(v_uni)}  -> {'OK' if same else 'DIFF'}")


# --------- 先確保有快取/索引（不強制重建）---------
print(cofacts_refresh_cache(force=False))

query = "mRNA 疫苗"

# HF-only
res_hf = cofacts_search_text(query, top_k=5, use_api=False, use_hf=True)
print(res_hf)
show_items("HF-only", res_hf, limit=3)

# API-only
res_api = cofacts_search_text(query, top_k=5, use_api=True, use_hf=False)
print(res_api)
show_items("API-only", res_api, limit=3)



# 對同一篇做 API vs Unified 對照（拿 HF-only 的第 1 筆）
if res_hf["items"]:
    first_id = res_hf["items"][0]["id"]
    compare_article(first_id)

# 判讀也看一下（HF-only）
vd = cofacts_summarize_verdict("維他命C可治療新冠？", threshold=0.2, use_api=False, use_hf=True)
print("\n== summarize_verdict (HF-only) ==")
print("verdict:", vd["verdict"])
print("scores:", vd.get("scores"))
print("evidence:", len(vd.get("evidence") or []))
```

---

