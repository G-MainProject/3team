# -*- coding: utf-8 -*-
"""
콘솔 출력용 요약 함수 모음.

price_to_json.py가 임포트하는 다음 함수들을 제공합니다:
- print_summary_kiwoom(data)
- print_summary_dart(dart_data)
- print_summary_merged(merged)
"""

from __future__ import annotations

from typing import Any, Dict


def _safe_get(d: Dict[str, Any], key: str, default: Any = "-") -> Any:
    try:
        v = d.get(key)
        return default if v is None else v
    except Exception:
        return default


def print_summary_kiwoom(data: Dict[str, Any]) -> None:
    """Kiwoom 응답(JSON dict 추정)을 간단히 요약 출력."""
    if not isinstance(data, dict):
        print("[Kiwoom 요약] 알 수 없는 데이터 형식")
        return

    # 가능한 필드(가벼운 방어적 접근)
    code = _safe_get(data, "stk_cd") or _safe_get(data, "code")
    name = _safe_get(data, "stk_nm") or _safe_get(data, "name")
    price = (
        _safe_get(data, "tp")
        or _safe_get(data, "price")
        or _safe_get(data, "trade_price")
    )

    print("[Kiwoom 요약]")
    print(f"- 종목: {name} ({code})")
    print(f"- 현재가/체결가: {price}")


def _fmt(v: Any) -> str:
    if v is None:
        return "-"
    try:
        return f"{int(v):,}"
    except Exception:
        return str(v)


def print_summary_dart(dart_data: Dict[str, Any]) -> None:
    """collect_recent_years() 반환 구조를 요약 출력."""
    if not isinstance(dart_data, dict):
        print("[DART 요약] 알 수 없는 데이터 형식")
        return

    stk = _safe_get(dart_data, "stock_code")
    fs_div = _safe_get(dart_data, "fs_div")
    years = dart_data.get("collected_years") or []
    print("[DART 요약]")
    print(f"- 종목코드: {stk} / FS: {fs_div}")
    print(f"- 수집연도: {years}")

    rows = dart_data.get("data") or []
    # 최근 연도만 1~2개 간략 표시
    for row in rows[-2:]:
        y = _safe_get(row, "year", "?")
        q = (row or {}).get("quarters") or {}
        fy_add = _safe_get(((row or {}).get("reports") or {}).get("FY", {}), "add")
        print(
            f"  · {y}: Q1={_fmt(q.get('Q1'))}, Q2={_fmt(q.get('Q2'))}, "
            f"Q3={_fmt(q.get('Q3'))}, Q4={_fmt(q.get('Q4'))}, FY(add)={_fmt(fy_add)}"
        )


def print_summary_merged(merged: Dict[str, Any]) -> None:
    """price_to_json이 최종 생성하는 병합 구조 요약."""
    if not isinstance(merged, dict):
        print("[병합 요약] 알 수 없는 데이터 형식")
        return

    stk = _safe_get(merged, "stock_code")
    created = _safe_get(merged, "created_at")
    print("[병합 요약]")
    print(f"- 종목코드: {stk}")
    print(f"- 생성시각: {created}")

    if merged.get("kiwoom") is not None:
        print("- Kiwoom: 포함")
        kd = (merged.get("kiwoom") or {}).get("data")
        if kd:
            print_summary_kiwoom(kd)
    else:
        print("- Kiwoom: 제외")

    if merged.get("dart") is not None:
        print("- DART: 포함")
        print_summary_dart(merged.get("dart") or {})
    else:
        print("- DART: 제외")


__all__ = [
    "print_summary_kiwoom",
    "print_summary_dart",
    "print_summary_merged",
]
