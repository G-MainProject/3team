# -*- coding: utf-8 -*-
"""DART Open API 클라이언트

재무제표 데이터를 수집해 `data/raws/dart/<corp_code>/...json`에 저장합니다.

특징
- UTF-8-SIG(.env) 로딩 및 BOM 정리로 인코딩 문제 최소화
- 보고서 코드/연결구분은 .env로 오버라이드 가능(`DART_REPRT_CODES`, `DART_FS_DIV`)
- CFS가 비어 있으면 OFS 대체 시도, 또 없으면 직전 연도 조회
- 단일 계정(fnlttSinglAcntAll)도 옵션으로 함께 저장
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Sequence

import requests
import csv
import io
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://opendart.fss.or.kr/api"
DEFAULT_REPRT_CODES = ("11011", "11012", "11013", "11014")  # 1Q, 반기, 3Q, 사업보고서
DEFAULT_FS_DIV = "CFS"  # 연결


def _find_project_root() -> Path:
    """.env 또는 data 디렉터리를 기준으로 프로젝트 루트를 추정."""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists() or (parent / "data").exists():
            return parent
    return current.parents[4]


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
    """회사별 재무제표(다중/단일 계정)를 수집하여 파일로 저장.

    Parameters
    - corp_codes: DART 법인번호 목록
    - year: 사업연도(예: 2024)
    - raw_dir: 저장 루트(기본: <project>/data/raws)
    - reprt_codes: 보고서 코드들(기본: .env→기본값)
    - fs_div: CFS(연결)/OFS(별도)
    - pause: 호출 간 대기(초)
    - single_accounts: 단일 계정명 리스트(옵션)
    - session: 외부 세션 주입(옵션)
    """

    _ensure_env_loaded()
    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        raise RuntimeError("DART_API_KEY 환경변수가 설정되어 있지 않습니다.")

    # 가능하다면 하루에 한 번 corpcode CSV를 비동기 방식으로 갱신한다
    try:
        _update_corpcode_csv_if_stale(api_key, max_age_hours=24)
    except Exception:
        pass

    raw_root = _resolve_raw_dir(raw_dir) / "dart"
    raw_root.mkdir(parents=True, exist_ok=True)

    # .env 오버라이드 처리
    env_codes = os.getenv("DART_REPRT_CODES")
    parsed_env_codes: tuple[str, ...] | None = None
    if env_codes:
        try:
            parts = [p.strip() for p in env_codes.replace(";", ",").split(",") if p.strip()]
            parts = tuple(p for p in parts if p.isdigit())
            parsed_env_codes = parts or None
        except Exception:
            parsed_env_codes = None
    env_fs_div = (os.getenv("DART_FS_DIV") or "").strip().upper()
    if env_fs_div:
        fs_div = env_fs_div

    # 우선순위: 인자 > .env > 기본값
    reprt_codes = tuple(reprt_codes or parsed_env_codes or DEFAULT_REPRT_CODES)
    corp_codes = tuple(dict.fromkeys(str(code).strip() for code in corp_codes if str(code).strip()))
    if not corp_codes:
        raise ValueError("corp_codes 인자가 비어 있습니다.")

    sess = session or requests.Session()
    saved: MutableMapping[str, list[Path]] = {}

    try:
        for corp_code in corp_codes:
            corp_dir = raw_root / corp_code
            corp_dir.mkdir(parents=True, exist_ok=True)

            # 1) 다중 계정(fnlttMultiAcnt)
            multi_records: list[dict] = []
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
                rows = list(data.get("list", []) or [])
                LOGGER.info(
                    "DART fnlttMultiAcnt corp=%s reprt=%s fs=%s year=%s status=%s rows=%d%s",
                    corp_code,
                    reprt_code,
                    fs_div,
                    year,
                    status,
                    len(rows),
                    f" message:{data.get('message')}" if data.get("message") else "",
                )
                if status != "000":
                    LOGGER.warning(
                        "fnlttMultiAcnt 실패 corp=%s reprt=%s status=%s message=%s",
                        corp_code,
                        reprt_code,
                        status,
                        data.get("message"),
                    )
                else:
                    multi_records.append(
                        {
                            "corp_code": corp_code,
                            "reprt_code": reprt_code,
                            "fs_div": fs_div,
                            "year": year,
                            "rows": rows,
                        }
                    )
                time.sleep(max(pause, 0.0))

            # 저장(있다면)
            if multi_records:
                multi_path = corp_dir / f"fnlttMultiAcnt_{year}.json"
                _write_json(multi_path, multi_records)
                saved.setdefault(corp_code, []).append(multi_path)

            # 1-보강) CFS가 비면 OFS 재시도
            if not any(rec.get("rows") for rec in multi_records):
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
                                "rows": list(data.get("list", []) or []),
                            }
                        )
                    time.sleep(max(pause, 0.0))
                if any(rec.get("rows") for rec in alt_records):
                    multi_records = alt_records
                    multi_path = corp_dir / f"fnlttMultiAcnt_{year}.json"
                    _write_json(multi_path, multi_records)
                    saved.setdefault(corp_code, []).append(multi_path)

            # 1-보강) 직전 연도 조회
            if not any(rec.get("rows") for rec in multi_records):
                prev_year = int(year) - 1
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
                                "rows": list(data.get("list", []) or []),
                            }
                        )
                    time.sleep(max(pause, 0.0))
                if multi_prev:
                    multi_prev_path = corp_dir / f"fnlttMultiAcnt_{prev_year}.json"
                    _write_json(multi_prev_path, multi_prev)
                    saved.setdefault(corp_code, []).append(multi_prev_path)

            # 2) 단일 계정(fnlttSinglAcntAll)
            if single_accounts:
                single_payloads: list[dict] = []
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
                                "fnlttSinglAcntAll 실패 corp=%s reprt=%s account=%s status=%s",
                                corp_code,
                                reprt_code,
                                account_name,
                                status,
                            )
                        else:
                            single_payloads.append(
                                {
                                    "corp_code": corp_code,
                                    "reprt_code": reprt_code,
                                    "account_nm": account_name,
                                    "rows": list(data.get("list", []) or []),
                                }
                            )
                        time.sleep(max(pause, 0.0))

                if single_payloads:
                    single_path = corp_dir / f"fnlttSinglAcntAll_{year}.json"
                    _write_json(single_path, single_payloads)
                    saved.setdefault(corp_code, []).append(single_path)
    finally:
        if session is None:
            sess.close()

    return saved


def _request_json(sess: requests.Session, endpoint: str, *, params: Mapping[str, str]):
    """공통 HTTP GET 래퍼."""

    url = f"{BASE_URL}/{endpoint}"
    response = sess.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def _write_json(path: Path, payload) -> None:
    """응답을 UTF-8(JSON pretty)로 저장."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    LOGGER.info("DART 파일 저장: %s", path)


_ENV_LOADED = False


def _ensure_env_loaded() -> None:
    """.env(UTF-8-SIG) 로딩 및 BOM 정리. 재진입 안전."""
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


def _resolve_raw_dir(raw_dir: str | Path | None) -> Path:
    """`data/raws` 루트 경로를 반환하고 보장 생성."""

    if raw_dir is None:
        project_root = _find_project_root()
        raw_dir = project_root / "data" / "raws"
    path = Path(raw_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# corpCode.xml을 내려받아 data/dart_corpcode.csv 파일을 매일 갱신한다
# ---------------------------------------------------------------------------

def _corpcode_csv_path() -> Path:
    root = _find_project_root()
    return root / "data" / "dart_corpcode.csv"


def _update_corpcode_csv_if_stale(api_key: str, *, max_age_hours: int = 24) -> Path | None:
    """``max_age_hours`` 동안은 data/dart_corpcode.csv를 한 번만 갱신한다.

    CSV가 없거나 오래되면 corpCode.xml을 내려받아 다시 작성하고,
    파이프라인이 중단되지 않도록 예외는 조용히 무시한다.
    """
    csv_path = _corpcode_csv_path()
    try:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    try:
        if csv_path.exists():
            mtime = datetime.fromtimestamp(csv_path.stat().st_mtime)
            if datetime.now() - mtime < timedelta(hours=max_age_hours):
                return csv_path
    except Exception:
        pass

    rows = _download_corpcode_rows(api_key)
    if not rows:
        # 실패 시 기존에 수집한 공시 원본으로부터 정보를 다시 구성한다
        try:
            rows = _build_corpcode_rows_from_raws()
        except Exception:
            rows = []
        if not rows:
            return None
    rows = _sort_corpcode_rows(rows)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["corp_code", "corp_name", "stock_code"])
        for r in rows:
            w.writerow([r.get("corp_code", ""), r.get("corp_name", ""), r.get("stock_code", "")])
    return csv_path


def _download_corpcode_rows(api_key: str) -> list[dict[str, str]]:
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    resp = requests.get(url, params={"crtfc_key": api_key}, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        name = next((n for n in zf.namelist() if n.lower().endswith(".xml")), None)
        if not name:
            return []
        xml_bytes = zf.read(name)
    root = ET.fromstring(xml_bytes)
    out: list[dict[str, str]] = []
    for el in root.findall("list"):
        corp_code = (el.findtext("corp_code") or "").strip()
        corp_name = (el.findtext("corp_name") or "").strip()
        stock_code = (el.findtext("stock_code") or "").strip()
        out.append({"corp_code": corp_code, "corp_name": corp_name, "stock_code": stock_code})
    return out


def _build_corpcode_rows_from_raws() -> list[dict[str, str]]:
    """기존 fnlttMultiAcnt 원본 데이터에서 corp_code→stock_code 매핑을 추출한다."""
    rows: dict[str, dict[str, str]] = {}
    root = _find_project_root() / "data" / "raws" / "dart"
    if not root.exists():
        return []
    for corp_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        corp_code = corp_dir.name.strip()
        multi_files = sorted(corp_dir.glob("fnlttMultiAcnt_*.json"))
        for mf in multi_files:
            try:
                payload = json.loads(mf.read_text(encoding="utf-8"))
            except Exception:
                continue
            found = False
            for rec in payload or []:
                for row in (rec.get("rows") or []):
                    stock_code = str(row.get("stock_code") or "").strip()
                    corp_name = str(row.get("corp_name") or row.get("corp_nm") or "").strip()
                    if stock_code:
                        rows[corp_code] = {
                            "corp_code": corp_code,
                            "corp_name": corp_name,
                            "stock_code": stock_code,
                        }
                        found = True
                        break
                if found:
                    break
            if found:
                break
    return list(rows.values())


def _sort_corpcode_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    def _key(row: dict[str, str]) -> tuple[int, str, str]:
        stock = (row.get("stock_code") or "").strip()
        corp = (row.get("corp_code") or "").strip()
        return (0 if stock else 1, stock, corp)

    return sorted(rows, key=_key)
