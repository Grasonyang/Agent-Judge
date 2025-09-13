from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

import pandas as pd

from .config import (
    DEBUG,
    HF_TOKEN,
    COFACTS_HF_LOCAL_DIR,
    COFACTS_HF_REFRESH_DAYS,
)

def _debug(msg: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {msg}")

HF_NAME = "Cofacts/line-msg-fact-check-tw"
_SPLITS = ("articles", "replies", "article_replies")


@dataclass
class _Tables:
    articles: pd.DataFrame
    replies: pd.DataFrame
    article_replies: pd.DataFrame


class HFClient:
    def __init__(self) -> None:
        self.root = Path(COFACTS_HF_LOCAL_DIR or "./.hf_cache")
        self.root.mkdir(parents=True, exist_ok=True)
        self.parquet_dir = self.root / "parquet"
        self.parquet_dir.mkdir(parents=True, exist_ok=True)

        self.tables: Optional[_Tables] = None
        self.last_sync_ts: Optional[str] = None

    # ---------- local checks ----------

    def _parquet_path(self, split: str) -> Path:
        return self.parquet_dir / f"{split}.parquet"

    def _local_parquet_ok(self) -> bool:
        ok = True
        for s in _SPLITS:
            p = self._parquet_path(s)
            if not p.exists() or p.stat().st_size == 0:
                ok = False
                break
        return ok

    def _rows_ok(self, t: _Tables) -> bool:
        # 三個表至少 articles > 0 就算有效
        return (len(t.articles) > 0)

    def _fresh_enough(self) -> bool:
        """根據檔案 mtime 與 refresh_days 判斷是否新鮮，但**必須**檔案存在且非空。"""
        if not self._local_parquet_ok():
            return False
        days = int(COFACTS_HF_REFRESH_DAYS or 0)
        if days <= 0:
            return False
        now = time.time()
        threshold = now - days * 86400
        for s in _SPLITS:
            if self._parquet_path(s).stat().st_mtime < threshold:
                return False
        return True

    # ---------- load / sync ----------

    def _read_local(self) -> _Tables:
        A = pd.read_parquet(self._parquet_path("articles"))
        R = pd.read_parquet(self._parquet_path("replies"))
        AR = pd.read_parquet(self._parquet_path("article_replies"))
        return _Tables(articles=A, replies=R, article_replies=AR)

    def _write_local(self, t: _Tables) -> None:
        t.articles.to_parquet(self._parquet_path("articles"), index=False)
        t.replies.to_parquet(self._parquet_path("replies"), index=False)
        t.article_replies.to_parquet(self._parquet_path("article_replies"), index=False)

    def _pull_from_hf(self) -> _Tables:
        try:
            from datasets import load_dataset
        except Exception as e:
            raise RuntimeError(f"datasets not installed: {e}")

        auth_kw = {}
        # 某些情況需要 token；若未提供會匿名下載公開資料
        if HF_TOKEN:
            auth_kw["token"] = HF_TOKEN

        try:
            A = load_dataset(HF_NAME, "articles", **auth_kw)["train"].to_pandas()
            R = load_dataset(HF_NAME, "replies", **auth_kw)["train"].to_pandas()
            AR = load_dataset(HF_NAME, "article_replies", **auth_kw)["train"].to_pandas()
        except Exception as e:
            # 常見：未同意 gated dataset、未登入、網路受限等
            raise RuntimeError(
                "Failed to load from Hugging Face. "
                "Possible causes: need to accept dataset terms, missing HF token, or network blocked. "
                f"Raw error: {type(e).__name__}: {e}"
            )

        return _Tables(articles=A, replies=R, article_replies=AR)

    def load(self, refresh: Optional[bool] = None) -> None:
        """
        載入資料：
        - 若 refresh=True → 強制重抓
        - 若 refresh=False → 優先讀本地
        - 若 refresh=None → 依新鮮度（且檔案非空）決定；一旦發現 0 筆，**一定重抓**
        """
        # 先試讀本地（若存在）
        if refresh is False and self._local_parquet_ok():
            t = self._read_local()
            if self._rows_ok(t):
                self.tables = t
                _debug("HF local parquet loaded (explicit refresh=False)")
                return
            # 本地有檔但 0 筆 → 仍會重抓
            _debug("HF local parquet exists but empty; will refresh")

        # 自動模式：檢查新鮮且非空才跳過
        if refresh is None and self._fresh_enough():
            try:
                t = self._read_local()
                if self._rows_ok(t):
                    self.tables = t
                    _debug("HF cache is fresh and non-empty; use local parquet")
                    return
                else:
                    _debug("HF cache claimed fresh but rows=0; will refresh")
            except Exception:
                _debug("HF cache read failed; will refresh")

        # 走遠端拉取
        _debug("Pulling HF datasets ...")
        t = self._pull_from_hf()
        if not self._rows_ok(t):
            # 這裡幾乎不會發生，除非 HF 真的回 0 筆
            raise RuntimeError("HF returned 0 rows. Are you authorized to access the dataset?")

        # 寫回本地
        self._write_local(t)
        self.tables = t
        self.last_sync_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _debug(f"HF synced: A={len(t.articles)} R={len(t.replies)} AR={len(t.article_replies)}")

    # ---------- joined rows ----------

    def joined_articles(self) -> Iterable[Dict]:
        """
        產生器：輸出統一結構：
          { id, text, createdAt, replyCount, articleReplies: [{id,type,text}] }
        """
        if not self.tables:
            raise RuntimeError("HFClient not loaded. Call load() first.")
        A, R, AR = self.tables.articles, self.tables.replies, self.tables.article_replies

        # replies map
        rmap = {
            str(r["id"]): {"id": str(r["id"]), "type": r.get("type"), "text": r.get("text")}
            for _, r in R.iterrows()
        }
        # article -> replies list
        amap: Dict[str, List[Dict]] = {}
        for _, link in AR.iterrows():
            aid = str(link.get("articleId"))
            rid = str(link.get("replyId"))
            if not aid or not rid:
                continue
            rr = rmap.get(rid)
            if rr:
                amap.setdefault(aid, []).append(rr)

        for _, a in A.iterrows():
            aid = str(a["id"])
            txt = a.get("text")
            created_at = a.get("createdAt")
            reps = amap.get(aid, [])
            rc = int(a.get("replyCount")) if pd.notna(a.get("replyCount")) else len(reps)
            yield {
                "id": aid,
                "text": txt,
                "createdAt": created_at,
                "replyCount": rc,
                "articleReplies": reps,
            }
