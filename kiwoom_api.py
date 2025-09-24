"""Kiwoom REST API 클라이언트 유틸리티."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, List

import requests


def _find_project_root() -> Path:
    """프로젝트 루트를 찾는다."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists() or (parent / "data").exists():
            return parent
    # Fallback for safety, might need adjustment
    return current.parents[3]


def _load_mock_data(path: str) -> Any:
    """목업 데이터를 로드한다."""
    full_path = _find_project_root() / "data" / "mock" / path
    if not full_path.exists():
        raise FileNotFoundError(f"Mock data not found: {full_path}")
    return json.loads(full_path.read_text(encoding="utf-8"))


_ENV_LOADED = False


def _load_env_if_needed() -> None:
    """환경변수를 한 번만 로딩한다."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    project_root = _find_project_root()
    env_path = project_root / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    _ENV_LOADED = True

def fetch_top_movers_direct(
    market: str = "KOSPI",
    count: int = 5,
    use_mock: bool = False,
    direction: str = "both",
) -> List[dict[str, Any]]:
    """
    Kiwoom API를 통해 직접 등락률 상위 종목을 가져옵니다.

    Args:
        market: 시장 구분 ("KOSPI", "KOSDAQ", "ALL")
        count: 가져올 종목 수
        use_mock: Mock 데이터를 사용할지 여부
        direction: "gainers", "losers", 또는 "both"

    Returns:
        등락률 상위 종목 리스트
    """
    _load_env_if_needed()

    if use_mock:
        print("[Kiwoom API] Using mock data for top movers.")
        mock_data = _load_mock_data("kiwoom_top_movers.json")
        return mock_data.get("data", [])[:count]

    base_url = os.environ.get("KIWOOM_API_URL")
    if not base_url:
        raise RuntimeError("KIWOOM_API_URL 환경 변수가 설정되지 않았습니다.")

    market_map = {"KOSPI": "0", "KOSDAQ": "101", "ALL": "0"}
    fid_input = {
        "rank_req_type": "1",
        "market_type": market_map.get(market, "0"),
        "vol_cond": "0",
        "rank_type": "0",
    }

    url = f"{base_url}/api/stock/top-movers"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=fid_input, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("success") or "data" not in data:
            raise RuntimeError(f"Kiwoom API error: {data.get('message', 'Unknown error')}")

        entries = []
        for item in data["data"]:
            try:
                entries.append(
                    {
                        "ticker": item.get("stock_code"),
                        "name": item.get("stock_name"),
                        "change_pct": float(item.get("fluctuation_rate", 0.0)),
                        "current_price": int(item.get("current_price", 0)),
                        "base_price": int(item.get("current_price", 0))
                        / (1 + float(item.get("fluctuation_rate", 0.0)) / 100.0),
                    }
                )
            except (ValueError, TypeError):
                continue  # 데이터 변환 실패 시 해당 항목은 건너뜁니다.

        # 등락률 절대값 기준으로 정렬
        entries.sort(key=lambda x: abs(x.get("change_pct", 0.0)), reverse=True)
        return entries[:count]

    except requests.RequestException as e:
        print(f"Error fetching from Kiwoom API: {e}", file=sys.stderr)
        raise RuntimeError("Kiwoom API 호출에 실패했습니다.") from e