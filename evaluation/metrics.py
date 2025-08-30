"""評估指標函式"""
from typing import List, Dict
import json
from urllib.request import urlopen
from urllib.error import URLError
from difflib import SequenceMatcher


def _fetch_wikipedia_summary(topic: str) -> str:
    """從維基百科取得條目摘要"""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
    try:
        with urlopen(url, timeout=5) as resp:  # type: ignore[arg-type]
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("extract", "")
    except (URLError, ValueError):
        return ""


def evaluate_truthfulness(debate: List[Dict]) -> float:
    """根據辯論訊息與外部查證資料計算真實性"""
    if not debate:
        return 0.0

    scores: List[float] = []
    for msg in debate:
        content = msg.get("content", "")
        topic = msg.get("topic")
        if not topic:
            scores.append(0.0)
            continue

        # 取得外部查證內容並計算語意相似度
        summary = _fetch_wikipedia_summary(topic)
        ratio = SequenceMatcher(None, content.lower(), summary.lower()).ratio()
        scores.append(ratio)

    return sum(scores) / len(scores)


def evaluate_consistency(debate: List[Dict]) -> float:
    """以訊息間語意相似度衡量辯論一致性"""
    if not debate:
        return 0.0

    contents = [m.get("content", "") for m in debate]
    if len(contents) == 1:
        return 1.0

    sims: List[float] = []
    for a, b in zip(contents, contents[1:]):
        ratio = SequenceMatcher(None, a.lower(), b.lower()).ratio()
        sims.append(ratio)

    return sum(sims) / len(sims)
