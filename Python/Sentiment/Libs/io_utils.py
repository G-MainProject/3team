# -*- coding: utf-8 -*-
from pathlib import Path
import json, time

# 프로젝트 루트 = 3team
ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"

def default_json_path(stk: str, ts: str | None = None) -> Path:
    """
    종목코드와 타임스탬프로 data 폴더 안에 저장 경로를 생성
    """
    if ts is None:
        ts = time.strftime("%Y%m%d_%H%M%S")
    return DATA_DIR / f"stock_{stk}_{ts}.json"

def save_json(obj, path: Path) -> str:
    """
    JSON 데이터를 지정한 경로에 저장
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)

def save_tsv(rows: list[list[str]], path: Path, headers: list[str] | None = None, include_header: bool = True) -> str:
    """
    Save rows to a tab-separated text file.
    - rows: list of list of stringifiable values
    - headers: optional header names
    - include_header: whether to write header row (default: True)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if headers and include_header:
        lines.append("\t".join(str(h) for h in headers))
    for row in rows:
        lines.append("\t".join("" if v is None else str(v) for v in row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)
