from typing import Optional
from pydantic import BaseModel


class Evidence(BaseModel):
    """通用證據資料模型"""
    source: str  # 證據來源（如網址或文獻）
    claim: str   # 證據支持的主張
    warrant: str  # 為何此來源支持該主張
    method: Optional[str] = None  # 取得或驗證證據的方法
    risk: Optional[str] = None  # 可能的風險或偏誤
    confidence: Optional[str] = None  # 對證據的信心程度


# ---- Curator 轉 Evidence ----
def curator_result_to_evidence(result, claim: str, warrant: str,
                              method: Optional[str] = None,
                              risk: Optional[str] = None,
                              confidence: Optional[str] = None) -> Evidence:
    """將 Curator 的搜尋結果轉為 Evidence"""
    url = getattr(result, "url", "")
    return Evidence(
        source=url,
        claim=claim,
        warrant=warrant,
        method=method,
        risk=risk,
        confidence=confidence,
    )
