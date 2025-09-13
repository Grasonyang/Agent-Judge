from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# =========================
# Load .env if available
# =========================

def _load_dotenv_if_any() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    # 尋找專案根目錄 .env
    cwd = Path.cwd()
    env_path = cwd / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

_load_dotenv_if_any()


# =========================
# Helpers
# =========================

def getenv_str(key: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(key, default)
    if v is None:
        return None
    v = str(v).strip()
    return v if v != "" else default

def getenv_int(key: str, default: int = 0) -> int:
    v = os.getenv(key)
    if v is None or str(v).strip() == "":
        return int(default)
    try:
        return int(str(v).strip())
    except Exception:
        return int(default)

def getenv_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return bool(default)
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "y", "on")

# === 全部寫死在這裡，不用 .env ===

# 調試
DEBUG: bool = True

# Cofacts API
COFACTS_API_URL: str = "https://api.cofacts.tw/graphql"
COFACTS_APP_ID: str | None = None
COFACTS_APP_SECRET: str | None = None
COFACTS_API_FIRST: int = 5000
COFACTS_API_CANDIDATES: int = 5000

# Hugging Face / 本地快取
HF_TOKEN: str=""              # 如需私有資源可填入字串，否則留 None
COFACTS_HF_LOCAL_DIR: str = "./.hf_cache" # unified/articles.jsonl 會存這裡
COFACTS_HF_REFRESH_DAYS: int = 7          # 0 = 每次都刷新；>0 為新鮮視窗

# 向量快取 / 索引
COFACTS_CACHE_ENABLE: bool = True
COFACTS_CACHE_DIR: str = "./.vector_cache"  # X.npz / ids.npy / vocab.json / meta.json

# TF-IDF 參數（中文推薦 char_wb, ngram 1~2, min_df 2）
COFACTS_TFIDF_ANALYZER: str = "char_wb"
COFACTS_TFIDF_MIN_DF: int = 2
COFACTS_TFIDF_NGRAM_MIN: int = 1
COFACTS_TFIDF_NGRAM_MAX: int = 2

# 搜尋行為
COFACTS_SEARCH_ENGINE: str = "bm25"  # tfidf | bm25 | sbert
DEFAULT_TOP_K: int = 5

# 匯出（若之後需要）
COFACTS_OUTPUT_DIR: str = "./cofacts_output"
COFACTS_OUTPUT_UTC: bool = False

# 網站基底（for models.Article.article_url）
COFACTS_WEB_BASE: str = "https://cofacts.org"

# ======= 自動建置控制（重要） =======
# 開機/首次使用自動建立 unified cache 與 TF-IDF 索引
COFACTS_AUTO_BOOTSTRAP: bool = True
# 啟動模式： "lazy" = 第一次 search() 再建；"eager" = import 時就建
COFACTS_AUTO_BOOTSTRAP_MODE: str = "lazy"   # "lazy" | "eager"
# 若已存在檔案是否仍強制重建
COFACTS_BOOTSTRAP_FORCE: bool = False
