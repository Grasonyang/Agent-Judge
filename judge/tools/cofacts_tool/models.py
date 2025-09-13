from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# 讀取網站基底位址用於組 article_url
from .config import COFACTS_WEB_BASE


def _norm_str(x: Optional[str]) -> Optional[str]:
    """將空字串/全空白正規化為 None，其他保持原值。"""
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None


def _ensure_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


class Reply(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None  # e.g., RUMOR / NOT_RUMOR / OPINIONATED / NOT_ARTICLE / UNSURE
    text: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Reply":
        """
        可接受兩種型態：
        1) 扁平：{"id":"...", "type":"...", "text":"..."}
        2) 巢狀：{"reply": {"id":"...", "type":"...", "text":"..."}}
        """
        if raw is None:
            return cls()

        node = raw.get("reply") if isinstance(raw.get("reply"), dict) else raw
        return cls(
            id=_norm_str(node.get("id")),
            type=_norm_str(node.get("type")),
            text=_norm_str(node.get("text")),
        )


class Article(BaseModel):
    id: str = ""
    text: Optional[str] = None
    createdAt: Optional[str] = None
    replyCount: int = 0
    articleReplies: List[Reply] = Field(default_factory=list)
    article_url: Optional[str] = None  # 方便前端/輸出直接使用

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Article":
        """
        將來自 API/HF/local-store 的雜訊資料統一成 Article。
        - 自動處理 articleReplies 的不同結構
        - 產生 article_url
        - 對空字串做 None 正規化
        """
        if raw is None:
            return cls()

        aid = _norm_str(raw.get("id")) or ""
        txt = _norm_str(raw.get("text"))
        created = _norm_str(raw.get("createdAt"))
        # 某些來源沒有 replyCount；保底為 0
        rcount = raw.get("replyCount")
        try:
            rcount = int(rcount) if rcount is not None else 0
        except Exception:
            rcount = 0

        # 統一 replies：可能是
        #   - "articleReplies": [{"reply": {...}}, ...]
        #   - "articleReplies": [{"id":..., "type":..., "text":...}, ...]
        #   - "replies": 同上（少數資料會用不同鍵）
        raw_replies = raw.get("articleReplies")
        if raw_replies is None:
            raw_replies = raw.get("replies")

        replies: List[Reply] = []
        for r in _ensure_list(raw_replies):
            try:
                replies.append(Reply.from_dict(r))
            except Exception:
                # 單筆壞資料忽略，避免整筆失敗
                continue

        # 組出文章連結（避免多餘斜線）
        base = (COFACTS_WEB_BASE or "").rstrip("/")
        article_url = f"{base}/article/{aid}" if aid else None

        return cls(
            id=aid,
            text=txt,
            createdAt=created,
            replyCount=rcount,
            articleReplies=replies,
            article_url=article_url,
        )


class SearchResult(BaseModel):
    query: str
    items: List[Article] = Field(default_factory=list)
    # source: 哪些通道有用到（api/hf/…），例如 {"api": True, "hf": True}
    source: Dict[str, bool] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        相容 Pydantic v2 (model_dump) 與 v1 (dict)。
        """
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()


__all__ = ["Reply", "Article", "SearchResult"]
