# -*- coding: utf-8 -*-
"""top_mover_forecast.json을 화면 표시 규칙에 맞춰 후처리합니다.

- fundamentals 딕셔너리의 *_display 키를 제거합니다.
- fundamentals_raw_display 섹션을 삭제합니다.
- 핵심 지표가 비어 있으면 '-' 문자로 채웁니다.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

MAIN_KEYS: List[str] = [
    "roe", "roa", "per", "pbr",
    "debt_ratio", "current_ratio", "quick_ratio", "equity_ratio",
]

def _is_number(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

def _fmt_item(key: str, value: Any) -> Dict[str, Any]:
    labels = {
        'roe': 'ROE',
        'roa': 'ROA',
        'per': 'PER',
        'pbr': 'PBR',
        'debt_ratio': 'Debt Ratio',
        'current_ratio': 'Current Ratio',
        'quick_ratio': 'Quick Ratio',
        'equity_ratio': 'Equity Ratio',
    }
    label = labels.get(key, key)
    if not _is_number(value):
        return {"key": key, "label": label, "value": None, "display": "-"}
    v = float(value)
    if key in ("roe", "roa"):
        return {"key": key, "label": label, "value": v, "display": f"{v*100.0:.2f}%"}
    if key in ("per", "pbr"):
        return {"key": key, "label": label, "value": v, "display": f"{v:.2f}x"}
    return {"key": key, "label": label, "value": v, "display": f"{v:.2f}%"}

def process(path: Path, out: Path | None = None) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    for entry in entries:
        if "fundamentals_raw_display" in entry:
            del entry["fundamentals_raw_display"]
        fund = entry.get("fundamentals")
        if isinstance(fund, dict):
            for k in list(fund.keys()):
                if k.endswith("_display"):
                    fund.pop(k, None)
        if not isinstance(fund, dict):
            fund = {}
            entry["fundamentals"] = fund
        for key in MAIN_KEYS:
            val = fund.get(key)
            if not _is_number(val):
                fund[key] = "-"
        if "fundamentals_display" in entry:
            del entry["fundamentals_display"]
    target = out if out is not None else path
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Top mover 리포트 JSON 후처리")
    parser.add_argument("--input", type=Path, default=Path("data/outputs/top_mover_forecast.json"))
    parser.add_argument("--output", type=Path, help="결과를 다른 파일로 저장 (선택 사항)")
    args = parser.parse_args(argv)
    process(args.input, args.output)
    print(f"후처리 완료 -> {str(args.output or args.input)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
