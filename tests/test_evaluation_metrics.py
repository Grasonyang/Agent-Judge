import sys
from pathlib import Path
from difflib import SequenceMatcher

sys.path.append(str(Path(__file__).resolve().parents[1]))

from evaluation import metrics
from evaluation.metrics import evaluate_truthfulness, evaluate_consistency


def test_truthfulness_uses_external_data(monkeypatch):
    """測試真實性評估與外部查證資料的整合"""
    debate = [{"role": "pro", "content": "Earth orbits the Sun", "topic": "Earth"}]

    def mock_fetch(topic: str) -> str:
        assert topic == "Earth"
        return "Earth orbits the Sun and is the third planet from the Sun."

    monkeypatch.setattr(metrics, "_fetch_wikipedia_summary", mock_fetch)

    score = evaluate_truthfulness(debate)
    expected = SequenceMatcher(
        None,
        debate[0]["content"].lower(),
        mock_fetch("Earth").lower(),
    ).ratio()
    assert score == expected


def test_consistency_similarity():
    """測試訊息語意相似度的一致性評估"""
    debate = [
        {"role": "pro", "content": "Cats are animals."},
        {"role": "con", "content": "Cats are animals indeed."},
        {"role": "judge", "content": "Dogs are unrelated."},
    ]

    score = evaluate_consistency(debate)
    s1 = SequenceMatcher(None, debate[0]["content"].lower(), debate[1]["content"].lower()).ratio()
    s2 = SequenceMatcher(None, debate[1]["content"].lower(), debate[2]["content"].lower()).ratio()
    expected = (s1 + s2) / 2
    assert score == expected

