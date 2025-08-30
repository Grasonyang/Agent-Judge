"""評估指標函式"""
from typing import List, Dict


def evaluate_truthfulness(debate: List[Dict]) -> float:
    """根據辯論訊息估算真實性分數"""
    if not debate:
        return 0.0
    total = len(debate)
    true_count = sum(1 for m in debate if "true" in m.get("content", "").lower())
    return true_count / total


def evaluate_consistency(debate: List[Dict]) -> float:
    """根據辯論訊息估算一致性分數"""
    if not debate:
        return 0.0
    speakers = [m.get("role") for m in debate]
    return 1.0 if len(set(speakers)) == 1 else 0.5
