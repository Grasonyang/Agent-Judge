import json
from pathlib import Path
from typing import Any


def _to_serializable(data: Any) -> Any:
    """將輸入資料轉為可被 `json` 序列化的型態"""
    # 若為 Pydantic BaseModel，先轉為 dict
    if hasattr(data, "model_dump"):
        return data.model_dump()
    return data

# 儲存圖片段（graphlet）到檔案系統
# name 為圖片段名稱，data 為 JSON 可序列化資料
# base_path 為基底資料夾路徑

def _graphlet_path(base_path: str, name: str) -> Path:
    """回傳指定圖片段的完整路徑"""
    base = Path(base_path)
    return base / f"{name}.json"


def save_graphlet(name: str, data: Any, base_path: str) -> str:
    """將圖片段資料寫入 JSON 檔並回傳路徑

    使用 `json.dump` 進行序列化寫入。
    """
    path = _graphlet_path(base_path, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = _to_serializable(data)
    with path.open("w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    return str(path)


def load_graphlet(name: str, base_path: str) -> Any:
    """讀取指定名稱的圖片段 JSON 資料

    使用 `json.load` 解析檔案內容。
    """
    path = _graphlet_path(base_path, name)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
