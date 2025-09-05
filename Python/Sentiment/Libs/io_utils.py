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
