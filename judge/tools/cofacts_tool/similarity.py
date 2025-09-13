from __future__ import annotations

import os
import math
import numpy as np
from typing import List, Optional, Sequence, Tuple

from .config import DEBUG, COFACTS_SEARCH_ENGINE, COFACTS_TFIDF_ANALYZER


def _debug(msg: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {msg}")


# =========================
# TF-IDF
# =========================

class TfidfEngine:
    def __init__(self, analyzer: Optional[str] = None) -> None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError as e:
            raise RuntimeError("scikit-learn is required for TF-IDF") from e

        self.analyzer = analyzer or (COFACTS_TFIDF_ANALYZER or "char_wb")
        self.vectorizer = TfidfVectorizer(analyzer=self.analyzer, ngram_range=(1, 2), min_df=2)
        self.matrix = None

    def fit(self, corpus: Sequence[str]) -> None:
        self.matrix = self.vectorizer.fit_transform(corpus)
        _debug(f"TfidfEngine: fitted on {len(corpus)} docs")

    def compute_scores(self, query: str) -> np.ndarray:
        if self.matrix is None:
            raise RuntimeError("TfidfEngine not fitted")
        qvec = self.vectorizer.transform([query])
        sims = (self.matrix @ qvec.T).toarray().ravel()
        return sims


# =========================
# BM25 (簡單 dense 實作)
# =========================

class BM25Engine:
    def __init__(self, corpus: Sequence[str]) -> None:
        self.corpus = [doc.split() for doc in corpus]
        self.doc_lens = [len(d) for d in self.corpus]
        self.avgdl = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 0.0
        self.df = {}
        for d in self.corpus:
            for w in set(d):
                self.df[w] = self.df.get(w, 0) + 1
        self.N = len(self.corpus)
        self.k1 = 1.5
        self.b = 0.75
        _debug(f"BM25Engine: fitted on {self.N} docs")

    def idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def compute_scores(self, query: str) -> np.ndarray:
        qterms = query.split()
        scores = np.zeros(self.N)
        for idx, doc in enumerate(self.corpus):
            score = 0.0
            doc_len = len(doc)
            for term in qterms:
                f = doc.count(term)
                if f == 0:
                    continue
                idf = self.idf(term)
                denom = f + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                score += idf * (f * (self.k1 + 1)) / denom
            scores[idx] = score
        return scores


# =========================
# SBERT (需 sentence-transformers)
# =========================

class SbertEngine:
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RuntimeError("sentence-transformers is required for SBERT engine") from e

        self.model = SentenceTransformer(model_name)
        self.embs = None

    def fit(self, corpus: Sequence[str]) -> None:
        self.embs = self.model.encode(corpus, convert_to_numpy=True, show_progress_bar=False)
        _debug(f"SbertEngine: encoded {len(corpus)} docs")

    def compute_scores(self, query: str) -> np.ndarray:
        if self.embs is None:
            raise RuntimeError("SbertEngine not fitted")
        qvec = self.model.encode([query], convert_to_numpy=True)[0]
        sims = np.dot(self.embs, qvec) / (np.linalg.norm(self.embs, axis=1) * np.linalg.norm(qvec) + 1e-9)
        return sims


# =========================
# Factory
# =========================

def get_engine(engine: Optional[str] = None,
               corpus: Optional[Sequence[str]] = None):
    """
    依名稱回傳 engine instance：
      - "tfidf"：需要先 fit()
      - "bm25"：建構時直接 fit(corpus)
      - "sbert"：需要先 fit()
    """
    name = (engine or COFACTS_SEARCH_ENGINE or "tfidf").lower()
    _debug(f"get_engine: {name}")

    if name == "tfidf":
        return TfidfEngine()
    elif name == "bm25":
        if corpus is None:
            raise ValueError("BM25 requires corpus at init")
        return BM25Engine(corpus)
    elif name == "sbert":
        return SbertEngine()
    else:
        raise ValueError(f"Unknown engine: {name}")
