from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .config import (
    DEBUG,
    # 若你的 config 沒這兩個值，給預設值
    COFACTS_OUTPUT_DIR as _CFG_OUT_DIR,
    COFACTS_OUTPUT_UTC as _CFG_OUT_UTC,
)

# 預設輸出資料夾與時區設定（避免 config 未定義時出錯）
DEFAULT_OUTPUT_DIR = "./cofacts_output"
OUTPUT_DIR = _CFG_OUT_DIR if _CFG_OUT_DIR else DEFAULT_OUTPUT_DIR
OUTPUT_USE_UTC = bool(int(_CFG_OUT_UTC)) if isinstance(_CFG_OUT_UTC, (str, int)) else bool(_CFG_OUT_UTC)


def _debug(msg: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {msg}")


def _ensure_dir(p: os.PathLike | str) -> Path:
    path = Path(p)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now() -> datetime:
    """
    依設定回傳現在時間：UTC 或本地時區。
    """
    return datetime.utcnow().replace(tzinfo=timezone.utc) if OUTPUT_USE_UTC else datetime.now().astimezone()


def _date_str(dt: Optional[datetime] = None) -> str:
    dt = dt or _now()
    return dt.strftime("%Y-%m-%d")


def _timestamp_str(dt: Optional[datetime] = None) -> str:
    dt = dt or _now()
    # 例：2025-09-13T16-30-05Z 或本地時區 2025-09-13T16-30-05+0800
    if OUTPUT_USE_UTC:
        return dt.strftime("%Y-%m-%dT%H-%M-%SZ")
    # 將冒號移除，避免 Windows 檔名問題
    return dt.strftime("%Y-%m-%dT%H-%M-%S%z")



def today_dir() -> Path:
    """
    依設定（UTC/本地）建立 cofacts_output/YYYY-MM-DD/ 並回傳路徑。
    """
    root = _ensure_dir(OUTPUT_DIR)
    d = _ensure_dir(root / _date_str())
    return d


def safe_filename(name: str, max_len: int = 120) -> str:
    """
    將任意字串轉成安全檔名（保留中英文、數字、-_ 和空白 → 空白轉下劃線）。
    """
    name = name.strip().replace(" ", "_")
    # 允許中文字、英數、-_. 其他都剔除
    name = re.sub(r"[^\w\-.一-鿿]", "", name, flags=re.UNICODE)
    if len(name) > max_len:
        name = name[:max_len]
    return name or "untitled"


def normalize_text_hash(text: Optional[str]) -> str:
    """
    對文字做簡單正規化（去前後空白、轉小寫）後回傳 SHA1。
    用於去重鍵或檔名摘要。
    """
    base = (text or "").strip().lower()
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


@dataclass
class ExportResult:
    path: Path
    count: int
    format: str  # "json" or "csv"


def _union_keys(rows: Iterable[Dict[str, Any]]) -> List[str]:
    keys: set[str] = set()
    for r in rows:
        keys.update(r.keys())
    return sorted(keys)


def _ordered_fields(preferred: Optional[Sequence[str]], rows: List[Dict[str, Any]]) -> List[str]:
    """
    欄位順序：preferred_fields（若存在且出現在資料中） + 其餘鍵（排序）。
    """
    all_keys = _union_keys(rows)
    if not preferred:
        return all_keys
    pref = [k for k in preferred if k in all_keys]
    rest = [k for k in all_keys if k not in pref]
    return pref + rest


def write_export(
    rows: List[Dict[str, Any]],
    fmt: str = "json",
    out: Optional[str] = None,
    preferred_fields: Optional[Sequence[str]] = None,
    default_basename: str = "search",
) -> ExportResult:
    """
    將查詢結果輸出為 JSON 或 CSV 檔案。
    - rows: 要輸出的 dict 列表
    - fmt: "json" 或 "csv"
    - out: 指定完整輸出路徑；若未指定，預設輸出到 cofacts_output/YYYY-MM-DD/<basename>-<ts>.<ext>
    - preferred_fields: CSV 欄位優先順序（其餘欄位自動排到後面）
    - default_basename: 未提供 out 時的檔名前綴
    回傳 ExportResult（含檔案路徑與筆數）
    """
    fmt = (fmt or "json").lower()
    if fmt not in ("json", "csv"):
        raise ValueError("fmt must be 'json' or 'csv'")

    # 目標路徑
    if out:
        out_path = Path(out)
        _ensure_dir(out_path.parent)
    else:
        folder = today_dir()
        ts = _timestamp_str()
        fname = f"{safe_filename(default_basename)}-{ts}.{fmt}"
        out_path = folder / fname

    _debug(f"write_export: fmt={fmt} out={out_path}")

    # 寫檔
    if fmt == "json":
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        return ExportResult(path=out_path, count=len(rows), format="json")

    # csv
    if not rows:
        # 沒資料也寫空檔（只含 header）
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(preferred_fields or [])
        return ExportResult(path=out_path, count=0, format="csv")

    fields = _ordered_fields(preferred_fields, rows)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return ExportResult(path=out_path, count=len(rows), format="csv")


__all__ = [
    "today_dir",
    "write_export",
    "safe_filename",
    "normalize_text_hash",
    "ExportResult",
]
