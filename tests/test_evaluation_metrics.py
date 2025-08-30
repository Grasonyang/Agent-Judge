import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from evaluation.metrics import evaluate_truthfulness, evaluate_consistency


def test_metrics_return_scores():
    """確保評估函式可以回傳分數"""
    debate = [
        {"role": "pro", "content": "This is true."},
        {"role": "con", "content": "This is false."},
    ]
    truth = evaluate_truthfulness(debate)
    consistency = evaluate_consistency(debate)
    assert truth == 0.5
    assert consistency == 0.5
