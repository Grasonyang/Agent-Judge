from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

import joblib
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from .config import (
    DEBUG,
    COFACTS_CACHE_DIR,
    COFACTS_HF_LOCAL_DIR,
    COFACTS_TFIDF_ANALYZER,
    COFACTS_TFIDF_MIN_DF,
    COFACTS_TFIDF_NGRAM_MIN,
    COFACTS_TFIDF_NGRAM_MAX,
    COFACTS_HF_REFRESH_DAYS,
    HF_TOKEN,
)
from .hf_client import HFClient


def _debug(msg: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {msg}")


def _ensure_dir(p: os.PathLike | str) -> Path:
    path = Path(p)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_jsonl(path: os.PathLike | str, rows: Iterable[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False))
            f.write("\n")


def _read_jsonl(path: os.PathLike | str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not Path(path).exists():
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def _write_json(path: os.PathLike | str, obj: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _read_json(path: os.PathLike | str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _line_count(p: Path) -> int:
    if not p.exists():
        return 0
    n = 0
    with p.open("r", encoding="utf-8") as f:
        for _ in f:
            n += 1
            if n >= 1_000_000:  # 夠用就好，避免超大檔慢數
                break
    return n


# ========================
# Unified HF store
# ========================

def has_unified_cache() -> bool:
    """非空檔才算有 unified cache。"""
    p = Path(COFACTS_HF_LOCAL_DIR).joinpath("unified", "articles.jsonl")
    return p.exists() and _line_count(p) > 0


def ensure_unified_cache(from_hf: bool = True, force: bool = False) -> Path:
    """
    產出本地 unified 倉（articles.jsonl + meta.json + ids.idx）。
    - 若檔案不存在、為空，或 force=True，會強制從 HF 重抓；
    - 抓回為 0 筆則 raise（避免把空檔寫回去）；
    - 生成 ids.idx：每行為 "<id>\\t<byte_offset>"，供快速隨機讀取。
    回傳 unified 目錄路徑。
    """
    root = _ensure_dir(COFACTS_HF_LOCAL_DIR)
    udir = _ensure_dir(root / "unified")
    articles_path = udir / "articles.jsonl"
    meta_path = udir / "meta.json"
    idx_path = udir / "ids.idx"

    need_rebuild = force or (not articles_path.exists()) or (_line_count(articles_path) == 0)

    if not need_rebuild:
        _debug("ensure_unified_cache: exists & non-empty; skip (force=False)")
        # 若舊版還沒 ids.idx，補建一次索引檔（單次掃描）
        if not idx_path.exists():
            _debug("ensure_unified_cache: ids.idx missing; building index from existing articles.jsonl ...")
            pos = 0
            with open(articles_path, "rb") as fin, open(idx_path, "w", encoding="utf-8") as fout:
                while True:
                    line = fin.readline()
                    if not line:
                        break
                    try:
                        d = json.loads(line.decode("utf-8"))
                        aid = str(d.get("id") or "").strip()
                        if aid:
                            fout.write(f"{aid}\t{pos}\n")
                    except Exception:
                        pass
                    pos = fin.tell()
        return udir

    if not from_hf:
        # 需要重建但又不允許從 HF 取數
        raise FileNotFoundError(f"Missing or empty {articles_path}; run with from_hf=True to materialize.")

    # 強制從 HF 抓，且抓不到就 raise
    hf = HFClient()
    hf.load(refresh=True)
    rows = list(hf.joined_articles())
    if not rows:
        raise RuntimeError(
            "ensure_unified_cache: HF returned 0 rows after refresh; "
            "please check dataset access / HF token / network."
        )

    # 同步寫入 JSONL（binary 模式，精準紀錄 byte offset），同時建 ids.idx
    with open(articles_path, "wb") as fout, open(idx_path, "w", encoding="utf-8") as iout:
        for r in rows:
            pos = fout.tell()
            b = (json.dumps(r, ensure_ascii=False) + "\n").encode("utf-8")
            fout.write(b)
            aid = str(r.get("id") or "").strip()
            if aid:
                iout.write(f"{aid}\t{pos}\n")

    meta = {
        "source": "hf",
        "row_count": len(rows),
        "last_sync_ts": hf.last_sync_ts or "",
        "refresh_days": int(COFACTS_HF_REFRESH_DAYS or 0),
        "token_used": bool(HF_TOKEN),
        "note": "Unified articles joined from HF datasets",
    }
    _write_json(meta_path, meta)
    _debug(f"ensure_unified_cache: wrote {len(rows)} rows")
    return udir


# ========================
# Vector index on unified store
# ========================

@dataclass
class _IndexPaths:
    root: Path
    X: Path
    ids: Path
    vec: Path
    meta: Path


def _get_index_paths() -> _IndexPaths:
    root = _ensure_dir(COFACTS_CACHE_DIR)
    return _IndexPaths(
        root=root,
        X=root / "X.npz",
        ids=root / "ids.npy",
        vec=root / "vectorizer.pkl",   # ★ 新增：持久化已訓練的 TfidfVectorizer
        meta=root / "meta.json",
    )


def has_index() -> bool:
    ip = _get_index_paths()
    return ip.X.exists() and ip.ids.exists() and ip.vec.exists()


def _make_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        analyzer=COFACTS_TFIDF_ANALYZER or "char_wb",
        min_df=int(COFACTS_TFIDF_MIN_DF or 2),
        ngram_range=(
            int(COFACTS_TFIDF_NGRAM_MIN or 1),
            int(COFACTS_TFIDF_NGRAM_MAX or 2),
        ),
    )


def build_index(unified_dir: Optional[os.PathLike | str] = None) -> Dict[str, Any]:
    """
    從 unified 文章倉建 TF-IDF 索引。
    - 儲存：X.npz（L2 正規化）、ids.npy、vectorizer.pkl、meta.json
    - 若 unified 為空，會先強制 refresh，再嘗試一次。
    """
    t0 = perf_counter()
    udir = Path(unified_dir) if unified_dir else ensure_unified_cache(from_hf=True)
    articles_path = udir / "articles.jsonl"
    meta_in = _read_json(udir / "meta.json") if (udir / "meta.json").exists() else {}

    rows = _read_jsonl(articles_path)
    if not rows:
        _debug("build_index: unified empty, forcing unified rebuild...")
        udir = ensure_unified_cache(from_hf=True, force=True)
        rows = _read_jsonl(udir / "articles.jsonl")

    ids: List[str] = []
    docs: List[str] = []
    for r in rows:
        aid = str(r.get("id") or "").strip()
        text = str(r.get("text") or "")
        if not aid or not text:
            continue
        ids.append(aid)
        docs.append(text)

    if not docs:
        raise RuntimeError("No documents found to build index.")

    vec = _make_vectorizer()
    _debug("Fitting TF-IDF ...")
    X = vec.fit_transform(docs)
    X = normalize(X, norm="l2", copy=False)

    ip = _get_index_paths()
    _ensure_dir(ip.root)
    sparse.save_npz(ip.X, X)
    np.save(ip.ids, np.array(ids, dtype=object))
    joblib.dump(vec, ip.vec)  # ★ 關鍵：存下「已訓練」的 Vectorizer

    meta_out = {
        "built_from": str(articles_path),
        "row_count": int(X.shape[0]),
        "feature_count": int(X.shape[1]),
        "vectorizer": {
            "analyzer": vec.analyzer if isinstance(vec.analyzer, str) else "callable",
            "min_df": vec.min_df,
            "ngram_range": list(vec.ngram_range),
        },
        "unified_meta": meta_in,
    }
    _write_json(ip.meta, meta_out)
    _debug(f"Index built in {perf_counter() - t0:.2f}s (rows={X.shape[0]}, feats={X.shape[1]})")
    return meta_out


@dataclass
class _LoadedIndex:
    X: sparse.csr_matrix
    ids: np.ndarray
    vectorizer: TfidfVectorizer


def _load_index() -> _LoadedIndex:
    ip = _get_index_paths()
    if not (ip.X.exists() and ip.ids.exists() and ip.vec.exists()):
        raise FileNotFoundError(
            f"Missing index files under {ip.root}. Run `build_index()` first."
        )
    _debug(f"Loading index from {ip.root} ...")
    X = sparse.load_npz(ip.X).tocsr()
    ids = np.load(ip.ids, allow_pickle=True)
    vec: TfidfVectorizer = joblib.load(ip.vec)  # ★ 直接載回已訓練 vectorizer
    return _LoadedIndex(X=X, ids=ids, vectorizer=vec)


def query_cached_similarity(query: str, top_n: int = 50) -> List[Tuple[str, float]]:
    """
    使用已建好的 TF-IDF 索引計算與 query 的 cosine 相似度。
    回傳 [(article_id, score), ...]，按分數由高到低。
    """
    if not query or not query.strip():
        return []
    li = _load_index()
    qv = li.vectorizer.transform([query])              # ★ 已訓練 vectorizer，transform 安全
    qv = normalize(qv, norm="l2", copy=False)
    sim = li.X.dot(qv.T).toarray().ravel()
    if sim.size == 0:
        return []
    n = min(top_n, sim.size)
    idx = np.argpartition(-sim, n - 1)[:n]
    idx = idx[np.argsort(-sim[idx])]
    return [(str(li.ids[i]), float(sim[i])) for i in idx]


# ========================
# Bootstrap
# ========================

def bootstrap_cache_and_index(force: bool = False) -> Dict[str, Any]:
    """
    若缺 unified 或索引，則自動建立。
    1) unified：若不存在或為空，或 force=True → rebuild from HF
    2) index：若不存在或 force=True → rebuild
    """
    out: Dict[str, Any] = {"unified": False, "index": False}

    # unified
    if force or (not has_unified_cache()):
        ensure_unified_cache(from_hf=True, force=True)
        out["unified"] = True
    else:
        _debug("bootstrap: unified exists & non-empty")

    # index
    ip = _get_index_paths()
    index_missing = not (ip.X.exists() and ip.ids.exists() and ip.vec.exists())
    if force or index_missing:
        build_index()
        out["index"] = True
    else:
        _debug("bootstrap: index exists")

    return out


__all__ = [
    "ensure_unified_cache",
    "has_unified_cache",
    "build_index",
    "query_cached_similarity",
    "bootstrap_cache_and_index",
]
