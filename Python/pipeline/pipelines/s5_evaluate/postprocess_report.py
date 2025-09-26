"""Post-process top_mover_forecast.json to match display requirements.

- Remove *_display keys from fundamentals dict
- Remove fundamentals_raw_display section
- Ensure fundamentals_display exists and includes the main ratio/multiple items
  (always present; if a value is missing, display '-')
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


# 지표 키: fundamentals에 항상 표기(없으면 '-')  # 한글 주석
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
        "roe": "ROE",
        "roa": "ROA",
        "per": "PER",
        "pbr": "PBR",
        "debt_ratio": "부채비율",
        "current_ratio": "유동비율",
        "quick_ratio": "당좌비율",
        "equity_ratio": "자기자본비율",
    }
    label = labels.get(key, key)
    if not _is_number(value):
        return {"key": key, "label": label, "value": None, "display": "-"}
    v = float(value)
    if key in ("roe", "roa"):
        return {"key": key, "label": label, "value": v, "display": f"{v*100.0:.2f}%"}
    if key in ("per", "pbr"):
        return {"key": key, "label": label, "value": v, "display": f"{v:.2f}x"}
    # percent metrics
    return {"key": key, "label": label, "value": v, "display": f"{v:.2f}%"}


def process(path: Path, out: Path | None = None) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    for entry in entries:
        # 1) drop fundamentals_raw_display  # 한글 주석
        if "fundamentals_raw_display" in entry:
            del entry["fundamentals_raw_display"]

        # 2) strip *_display from fundamentals dict  # 한글 주석
        fund = entry.get("fundamentals")
        if isinstance(fund, dict):
            for k in list(fund.keys()):
                if k.endswith("_display"):
                    fund.pop(k, None)

        # 3) ensure fundamentals keys always exist in fundamentals (no fundamentals_display)  # 한글 주석
        if not isinstance(fund, dict):
            fund = {}
            entry["fundamentals"] = fund
        for key in MAIN_KEYS:
            val = fund.get(key)
            if not _is_number(val):
                # 값이 없으면 '-'로 표기하라는 요구사항 반영  # 한글 주석
                fund[key] = "-"

        # 4) remove fundamentals_display entirely  # 한글 주석
        if "fundamentals_display" in entry:
            del entry["fundamentals_display"]

    target = out if out is not None else path
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Post-process top mover report JSON")
    parser.add_argument("--input", type=Path, default=Path("data/outputs/top_mover_forecast.json"))
    parser.add_argument("--output", type=Path, help="Write to a different file (optional)")
    args = parser.parse_args(argv)
    process(args.input, args.output)
    print(f"Post-processed -> {str(args.output or args.input)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
