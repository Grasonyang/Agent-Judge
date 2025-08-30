import pytest
from pydantic import ValidationError

# 測試 Skeptic 的輸出結構
from root_agent.agents.skeptic.agent import SkepticOutput, skeptic_schema_agent


def test_skeptic_schema_agent_schema():
    """確認代理人使用正確的輸出 Schema"""
    assert skeptic_schema_agent.output_schema is SkepticOutput
    assert skeptic_schema_agent.output_key == "skepticism"


def test_skeptic_output_validation():
    """驗證合法的 SkepticOutput 結構"""
    data = {
        "counter_thesis": "反方命題",
        "challenges": ["質疑一", "質疑二"],
        "evidence": [
            {
                "source": "https://example.com",
                "claim": "主張",
                "warrant": "理由",
            }
        ],
        "open_questions": ["待查問題"],
    }
    result = SkepticOutput.model_validate(data)
    assert result.counter_thesis == "反方命題"


def test_skeptic_output_invalid():
    """缺少必要欄位時應拋出錯誤"""
    data = {
        "counter_thesis": "反方命題",
        "challenges": ["質疑一"],
        "evidence": [],
        # 少了 open_questions
    }
    with pytest.raises(ValidationError):
        SkepticOutput.model_validate(data)
