# -*- coding: utf-8 -*-
"""Pull financial statement data from DART Open API and store under data/raws."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Sequence

import requests

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://opendart.fss.or.kr/api"
DEFAULT_REPRT_CODES = ("11011", "11012", "11013", "11014")
DEFAULT_FS_DIV = "CFS"


def _find_project_root() -> Path:
    """?섍꼍?뚯씪(.env)怨?data ?붾젆?곕━瑜?湲곗??쇰줈 ?꾨줈?앺듃 猷⑦듃瑜?李얜뒗??"""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists() or (parent / "data").exists():
            return parent
    return current.parents[4]


# DART ?щТ?쒗몴 API瑜??몄텧??raw/dart ?댄븯??JSON?쇰줈 ??ν븳??
def fetch_filings(
    *,
    corp_codes: Iterable[str],
    year: int,
    raw_dir: str | Path | None = None,
    reprt_codes: Sequence[str] | None = None,
    fs_div: str = DEFAULT_FS_DIV,
    pause: float = 0.25,
    single_accounts: Sequence[str] | None = None,
    session: requests.Session | None = None,
) -> Mapping[str, list[Path]]:
    """Fetch multi-account and optional single-account statements per company."""

    _ensure_env_loaded()
    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        raise RuntimeError("DART_API_KEY ?섍꼍蹂?섍? ?ㅼ젙?섏뼱 ?덉뼱???⑸땲??")

    raw_root = _resolve_raw_dir(raw_dir) / "dart"
    raw_root.mkdir(parents=True, exist_ok=True)

    # .env 湲곕컲 ?ㅻ쾭?쇱씠?? DART_REPRT_CODES, DART_FS_DIV
    env_codes = os.getenv("DART_REPRT_CODES")
    parsed_env_codes: tuple[str, ...] | None = None
    if env_codes:
        try:
            parts = [p.strip() for p in env_codes.replace(";", ",").split(",") if p.strip()]
            parts = [p for p in parts if p.isdigit()]
            if parts:
                parsed_env_codes = tuple(parts)
        except Exception:
            parsed_env_codes = None
    env_fs_div = os.getenv("DART_FS_DIV")
    if env_fs_div:
        try:
            fs_div = str(env_fs_div).strip().upper() or fs_div
        except Exception:
            pass

    # 최종 reprt_codes 결정: 인자 > .env > 기본
    reprt_codes = tuple(reprt_codes or parsed_env_codes or DEFAULT_REPRT_CODES)
    corp_codes = tuple(dict.fromkeys(str(code).strip() for code in corp_codes if str(code).strip()))
    if not corp_codes:
        raise ValueError("corp_codes???좏슚??媛믪씠 ?놁뒿?덈떎.")

    sess = session or requests.Session()
    saved: MutableMapping[str, list[Path]] = {}

    try:
        for corp_code in corp_codes:
            corp_dir = raw_root / corp_code
            corp_dir.mkdir(parents=True, exist_ok=True)

            multi_records = []
            for reprt_code in reprt_codes:
                payload = {
                    "crtfc_key": api_key,
                    "corp_code": corp_code,
                    "bsns_year": str(year),
                    "reprt_code": reprt_code,
                    "fs_div": fs_div,
                }
                data = _request_json(sess, "fnlttMultiAcnt.json", params=payload)
                status = data.get("status")
                try:
                    rows_cnt = len(data.get("list", []) or [])
                except Exception:
                    rows_cnt = 0
                LOGGER.info(
                    "DART fnlttMultiAcnt corp:%s reprt:%s status:%s rows:%s%s",
                    corp_code,
                    reprt_code,
                    status,
                    rows_cnt,
                    f" message:{data.get('message')}" if data.get("message") else "",
                )
                if status != "000":
                    LOGGER.warning(
                        "fnlttMultiAcnt failed - corp:%s reprt:%s status:%s message:%s",
                        corp_code,
                        reprt_code,
                        status,
                        data.get("message"),
                    )
                    continue
                multi_records.append(
                    {
                        "corp_code": corp_code,
                        "reprt_code": reprt_code,
                        "fs_div": fs_div,
                        "year": year,
                        "rows": data.get("list", []),
                    }
                )
                time.sleep(max(pause, 0))  # ?몄텧 ?쒗븳???쇳븯湲??꾪븳 ?щ┰

            multi_path = corp_dir / f"fnlttMultiAcnt_{year}.json"
            _write_json(multi_path, multi_records)
            saved.setdefault(corp_code, []).append(multi_path)

            # 異붽?: ?꾨뀈??蹂닿퀬?쒕룄 ??긽 ?섏쭛?섏뿬 TTM(理쒓렐 4遺꾧린) 援ъ꽦 蹂댁옣
            try:
                prev_year = int(year) - 1
            except Exception:
                prev_year = year
            multi_prev: list[dict] = []
            for reprt_code in reprt_codes:
                payload = {
                    "crtfc_key": api_key,
                    "corp_code": corp_code,
                    "bsns_year": str(prev_year),
                    "reprt_code": reprt_code,
                    "fs_div": fs_div,
                }
                data = _request_json(sess, "fnlttMultiAcnt.json", params=payload)
                status = data.get("status")
                if status == "000":
                    multi_prev.append(
                        {
                            "corp_code": corp_code,
                            "reprt_code": reprt_code,
                            "fs_div": fs_div,
                            "year": prev_year,
                            "rows": data.get("list", []),
                        }
                    )
                time.sleep(max(pause, 0))
            if multi_prev:
                multi_prev_path = corp_dir / f"fnlttMultiAcnt_{prev_year}.json"
                _write_json(multi_prev_path, multi_prev)
                saved.setdefault(corp_code, []).append(multi_prev_path)
            # ?대갚: ?ы빐 ?곗씠?곌? ?꾪? ?놁쑝硫?吏곸쟾 ?곕룄 ??踰????쒕룄
            try:
                has_any_rows = any(rec.get("rows") for rec in multi_records)
            except Exception:
                has_any_rows = False
            # CFS가 비어있으면 OFS(개별)로 대체 시도
            if not has_any_rows:
                try:
                    alt_records: list[dict] = []
                    for reprt_code in reprt_codes:
                        payload = {
                            "crtfc_key": api_key,
                            "corp_code": corp_code,
                            "bsns_year": str(year),
                            "reprt_code": reprt_code,
                            "fs_div": "OFS",
                        }
                        data = _request_json(sess, "fnlttMultiAcnt.json", params=payload)
                        if data.get("status") == "000":
                            alt_records.append(
                                {
                                    "corp_code": corp_code,
                                    "reprt_code": reprt_code,
                                    "fs_div": "OFS",
                                    "year": year,
                                    "rows": data.get("list", []),
                                }
                            )
                        time.sleep(max(pause, 0))
                    if any(rec.get("rows") for rec in alt_records):
                        multi_records = alt_records
                        multi_path = corp_dir / f"fnlttMultiAcnt_{year}.json"
                        _write_json(multi_path, multi_records)
                        saved.setdefault(corp_code, []).append(multi_path)
                        has_any_rows = True
                except Exception:
                    pass
            if not has_any_rows:
                try:
                    prev_year = int(year) - 1
                except Exception:
                    prev_year = year
                multi_prev: list[dict] = []
                for reprt_code in reprt_codes:
                    payload = {
                        "crtfc_key": api_key,
                        "corp_code": corp_code,
                        "bsns_year": str(prev_year),
                        "reprt_code": reprt_code,
                        "fs_div": fs_div,
                    }
                    data = _request_json(sess, "fnlttMultiAcnt.json", params=payload)
                    if data.get("status") == "000":
                        multi_prev.append(
                            {
                                "corp_code": corp_code,
                                "reprt_code": reprt_code,
                                "fs_div": fs_div,
                                "year": prev_year,
                                "rows": data.get("list", []),
                            }
                        )
                    time.sleep(max(pause, 0))
                if multi_prev:
                    multi_prev_path = corp_dir / f"fnlttMultiAcnt_{prev_year}.json"
                    _write_json(multi_prev_path, multi_prev)
                    saved.setdefault(corp_code, []).append(multi_prev_path)

            if single_accounts:
                single_payloads = []
                for reprt_code in reprt_codes:
                    for account_name in single_accounts:
                        payload = {
                            "crtfc_key": api_key,
                            "corp_code": corp_code,
                            "bsns_year": str(year),
                            "reprt_code": reprt_code,
                            "fs_div": fs_div,
                            "account_nm": account_name,
                        }
                        data = _request_json(sess, "fnlttSinglAcntAll.json", params=payload)
                        status = data.get("status")
                        if status != "000":
                            LOGGER.warning(
                                "fnlttSinglAcntAll failed - corp:%s reprt:%s account:%s status:%s",
                                corp_code,
                                reprt_code,
                                account_name,
                                status,
                            )
                            continue
                        single_payloads.append(
                            {
                                "corp_code": corp_code,
                                "reprt_code": reprt_code,
                                "account_nm": account_name,
                                "rows": data.get("list", []),
                            }
                        )
                        time.sleep(max(pause, 0))

                if single_payloads:
                    single_path = corp_dir / f"fnlttSinglAcntAll_{year}.json"
                    _write_json(single_path, single_payloads)
                    saved[corp_code].append(single_path)
    finally:
        if session is None:
            sess.close()

    return saved


def _request_json(sess: requests.Session, endpoint: str, *, params: Mapping[str, str]):
    """怨듯넻 HTTP GET ?섑띁."""

    url = f"{BASE_URL}/{endpoint}"
    response = sess.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def _write_json(path: Path, payload) -> None:
    """JSON ?묐떟??pretty ?щ㎎?쇰줈 ???"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    LOGGER.info("DART file saved: %s", path)


_ENV_LOADED = False


def _ensure_env_loaded() -> None:
    """Load .env with UTF-8-SIG and sanitize BOM (idempotent)."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    try:
        from Python.pipeline.utils.env import load_dotenv_utf8sig, sanitize_environ_bom
    except Exception:
        def load_dotenv_utf8sig() -> None:  # type: ignore
            return None
        def sanitize_environ_bom() -> None:  # type: ignore
            return None
    try:
        load_dotenv_utf8sig()
        sanitize_environ_bom()
    except Exception:
        pass
    _ENV_LOADED = True


def _load_env_utf8() -> None:
    """??踰덈쭔 .env瑜??쎌뼱 ?섍꼍蹂?섏뿉 諛섏쁺?쒕떎."""

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


def _resolve_raw_dir(raw_dir: str | Path | None) -> Path:
    """raw/dart 寃쎈줈瑜?怨꾩궛?쒕떎."""

    if raw_dir is None:
        project_root = _find_project_root()
        raw_dir = project_root / "data" / "raws"
    path = Path(raw_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path



