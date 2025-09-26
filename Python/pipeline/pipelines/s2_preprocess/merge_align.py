"""Utilities for merging raw inputs into bronze-level daily datasets."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
import numpy as np

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class MergeConfig:
    """브론즈 병합 단계에서 공통으로 쓰이는 파라미터 묶음."""

    tickers: Iterable[str]
    raw_root: Path
    bronze_root: Path
    price_source: str = "pykrx"
    news_dir: Optional[Path] = None
    fundamentals_dir: Optional[Path] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(
    *,
    tickers: Iterable[str] | None = None,
    raw_root: str | Path | None = None,
    bronze_root: str | Path | None = None,
    price_source: str = "pykrx",
    news_dir: str | Path | None = None,
    fundamentals_dir: str | Path | None = None,
) -> list[Path]:
    """Process all ``tickers`` and return the written bronze file paths."""

    resolved_raw = _resolve_raw_root(raw_root)
    target_tickers = list(tickers) if tickers else _discover_raw_tickers(resolved_raw, price_source)
    if not target_tickers:
        raise RuntimeError("raw 데이터에서 처리할 티커를 찾을 수 없습니다.")

    config = MergeConfig(
        tickers=target_tickers,
        raw_root=resolved_raw,
        bronze_root=_resolve_bronze_root(bronze_root),
        price_source=price_source.lower(),
        news_dir=Path(news_dir) if news_dir else None,
        fundamentals_dir=Path(fundamentals_dir) if fundamentals_dir else None,
    )
    outputs: list[Path] = []
    for ticker in config.tickers:
        try:
            outputs.append(_build_single_bronze(ticker, config))
        except FileNotFoundError as exc:
            LOGGER.warning("Skipping %s: %s", ticker, exc)
    return outputs


def merge_sources(
    *,
    ticker: str,
    raw_root: str | Path | None = None,
    bronze_root: str | Path | None = None,
    price_source: str = "pykrx",
    news_dir: str | Path | None = None,
    fundamentals_dir: str | Path | None = None,
) -> Path:
    """Merge sources for a single ``ticker`` and return the output path."""

    config = MergeConfig(
        tickers=[ticker],
        raw_root=_resolve_raw_root(raw_root),
        bronze_root=_resolve_bronze_root(bronze_root),
        price_source=price_source.lower(),
        news_dir=Path(news_dir) if news_dir else None,
        fundamentals_dir=Path(fundamentals_dir) if fundamentals_dir else None,
    )
    return _build_single_bronze(ticker, config)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_single_bronze(ticker: str, config: MergeConfig) -> Path:
    """개별 티커에 대한 가격/재무/뉴스 데이터를 병합한다."""

    price_df = _load_price_frame(ticker, config)
    fundamental_df = _load_fundamentals2(ticker, config)
    news_df = _load_news_features(ticker, config)

    frames = [price_df]
    if fundamental_df is not None and not fundamental_df.empty:
        frames.append(fundamental_df)
    if news_df is not None and not news_df.empty:
        frames.append(news_df)

    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.join(frame, how="left")

    merged = _fill_calendar_and_missing(merged)

    # DART 연계 재무값이 있을 경우 재무 비율 파생
    for col in (
        "fund_net_income_ttm",
        "fund_net_income",
        "fund_equity",
        "fund_assets",
        "fund_liabilities",
        "fund_current_assets",
        "fund_current_liabilities",
        "fund_inventories",
        "market_cap",
    ):
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce")

    if "fund_net_income_ttm" in merged.columns and "fund_equity" in merged.columns:
        merged["roe"] = (merged["fund_net_income_ttm"] / merged["fund_equity"])\
            .replace([np.inf, -np.inf], np.nan)
    if "fund_net_income_ttm" in merged.columns and "fund_assets" in merged.columns:
        merged["roa"] = (merged["fund_net_income_ttm"] / merged["fund_assets"])\
            .replace([np.inf, -np.inf], np.nan)
    if "market_cap" in merged.columns and "fund_net_income_ttm" in merged.columns:
        merged["per"] = (merged["market_cap"] / merged["fund_net_income_ttm"])\
            .replace([np.inf, -np.inf], np.nan)
    if "market_cap" in merged.columns and "fund_equity" in merged.columns:
        merged["pbr"] = (merged["market_cap"] / merged["fund_equity"])\
            .replace([np.inf, -np.inf], np.nan)
    # Additional ratios from DART
    if "fund_liabilities" in merged.columns and "fund_equity" in merged.columns:
        merged["debt_ratio"] = (merged["fund_liabilities"] / merged["fund_equity"]) * 100.0
        merged["debt_ratio"] = merged["debt_ratio"].replace([np.inf, -np.inf], np.nan)
    if "fund_current_assets" in merged.columns and "fund_current_liabilities" in merged.columns:
        merged["current_ratio"] = (merged["fund_current_assets"] / merged["fund_current_liabilities"]) * 100.0
        merged["current_ratio"] = merged["current_ratio"].replace([np.inf, -np.inf], np.nan)
        if "fund_inventories" in merged.columns:
            merged["quick_ratio"] = ((merged["fund_current_assets"] - merged["fund_inventories"]) / merged["fund_current_liabilities"]) * 100.0
            merged["quick_ratio"] = merged["quick_ratio"].replace([np.inf, -np.inf], np.nan)
    if "fund_equity" in merged.columns and "fund_assets" in merged.columns:
        merged["equity_ratio"] = (merged["fund_equity"] / merged["fund_assets"]) * 100.0
        merged["equity_ratio"] = merged["equity_ratio"].replace([np.inf, -np.inf], np.nan)
    merged["ticker"] = ticker

    config.bronze_root.mkdir(parents=True, exist_ok=True)
    target = config.bronze_root / f"{ticker}.parquet"
    output_path = _write_table(merged.reset_index().rename(columns={"index": "date"}), target)
    LOGGER.info("Bronze dataset saved: %s", output_path)
    return output_path


def _load_price_frame(ticker: str, config: MergeConfig) -> pd.DataFrame:
    """원천 가격 데이터(pykrx/kiwoom)를 읽어 특징표로 변환.

    우선순위: kiwoom -> pykrx. 특정 소스가 없거나 최신 파일이 없으면 다른 소스로 폴백한다.
    """

    kiwoom_dir = config.raw_root / "kiwoom" / ticker
    pykrx_dir = config.raw_root / "pykrx" / ticker

    # Try Kiwoom first
    if kiwoom_dir.exists():
        try:
            return _load_kiwoom_price(kiwoom_dir)
        except FileNotFoundError:
            pass

    # Fallback to pykrx
    if pykrx_dir.exists():
        return _load_pykrx_price(pykrx_dir)

    raise FileNotFoundError(f"Price directory not found: {kiwoom_dir} or {pykrx_dir}")


def _load_pykrx_price(directory: Path) -> pd.DataFrame:
    """pykrx JSON 구조를 DataFrame으로 변환한다."""

    ohlcv_path = _latest_file(directory, "ohlcv_daily")
    if ohlcv_path is None:
        raise FileNotFoundError(f"No pykrx ohlcv file in {directory}")
    df = _read_json_table(ohlcv_path)
    df.rename(columns={"value": "tr_value"}, inplace=True)

    for prefix in ("market_cap", "fundamental"):
        extra_path = _latest_file(directory, prefix)
        if extra_path is None:
            continue
        extra = _read_json_table(extra_path)
        df = df.merge(extra, on="date", how="left")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _load_kiwoom_price(directory: Path) -> pd.DataFrame:
    """키움 REST 응답(JSON)을 표준 칼럼으로 정리한다."""

    daily_path = _latest_file(directory, "ka10001")
    if daily_path is None:
        raise FileNotFoundError(f"No kiwoom ka10001 file in {directory}")

    payload = _read_json(daily_path)
    response = payload.get("response", {}) if isinstance(payload, dict) else {}
    rows = response.get("output") or response.get("items")
    if not rows and isinstance(response, dict):
        rows = response.get("data") or response.get("body")
    if not rows:
        raise FileNotFoundError(f"Kiwoom ka10001 response empty: {daily_path}")

    df = pd.DataFrame(rows)
    rename_map = {
        "trd_date": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "tr_value": "tr_value",
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)
    if "date" not in df.columns:
        df["date"] = df.get("trd_date")
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["date"])
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _load_fundamentals(ticker: str, config: MergeConfig) -> Optional[pd.DataFrame]:
    """DART 다중계정 JSON을 읽어 재무 지표를 생성한다."""

    root = config.fundamentals_dir or config.raw_root / "dart"
    if not root.exists():
        return None

    files = list(root.glob("*/fnlttMultiAcnt_*.json"))
    if not files:
        # 보조 경로: <project>/Python/data/raw/dart 에 저장된 경우 대응
        try:
            alt_root = _find_project_root() / "Python" / "data" / "raw" / "dart"
            if alt_root.exists():
                files = list(alt_root.glob("*/fnlttMultiAcnt_*.json"))
        except Exception:
            files = []
    if not files:
        return None

    # corp_code 기반 필터링: data/dart_corpcode.csv에서 ticker->corp_code 매핑 시도  # 한글 주석
    try:
        def _base(code: str) -> str:
            digits = "".join(ch for ch in str(code).strip() if ch.isdigit())
            if not digits:
                return str(code).zfill(6)
            d = digits.zfill(6)
            return d[:-1] + '0'
        expected_corp: str | None = None
        base_ticker = _base(ticker)
        csv_path = _find_project_root() / "data" / "dart_corpcode.csv"
        if csv_path.exists():
            import csv as _csv
            with csv_path.open("r", encoding="utf-8") as fp:
                rdr = _csv.DictReader(fp)
                headers = {h.lower(): h for h in (rdr.fieldnames or [])}
                t_col = headers.get("ticker") or headers.get("stock_code") or headers.get("code") or headers.get("symbol")
                c_col = headers.get("corp_code") or headers.get("corpcode") or headers.get("corpcode_id") or headers.get("corp")
                if t_col and c_col:
                    for row in rdr:
                        t = _base(row.get(t_col, ""))
                        c = str(row.get(c_col, "")).strip()
                        if t == base_ticker and c:
                            expected_corp = c
                            break
        if expected_corp:
            files = [p for p in files if p.parent.name == expected_corp]
    except Exception:
        pass

    frames: list[pd.DataFrame] = []
    for path in files:
        try:
            frame = _parse_dart_multi(path, ticker)
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.debug("Fundamental parse failed for %s: %s", path, exc)
            continue
        if frame is not None and not frame.empty:
            frames.append(frame)
    if not frames:
        return None

    df = pd.concat(frames, axis=0).sort_index()
    df = df.groupby(level=0).last()
    return df


def _parse_dart_multi(path: Path, ticker: str) -> Optional[pd.DataFrame]:
    """fnlttMultiAcnt JSON 구조를 pivot하여 feature 형태로 변환."""

    payload = _read_json(path)
    if not isinstance(payload, list):
        return None

    frames: list[pd.DataFrame] = []
    for entry in payload:
        rows = entry.get("rows", [])
        if not rows:
            continue
        df = pd.DataFrame(rows)
        if "stock_code" in df.columns:
            try:
                # stock_code가 비어 있지 않은 경우에만 필터 적용 (비어 있으면 corp_code 디렉터리 신뢰)
                if df["stock_code"].notna().any():
                    def _base(code: object) -> str:
                        raw = str(code or "").strip()
                        digits = "".join(ch for ch in raw if ch.isdigit())
                        if not digits:
                            return raw.zfill(6)
                        d = digits.zfill(6)
                        return d[:-1] + '0'
                    tick_base = _base(ticker)
                    codes = df["stock_code"].astype(str).map(_base).unique()
                    if tick_base not in codes:
                        continue
            except Exception:
                pass
        if "thstrm_amount" not in df.columns or "account_nm" not in df.columns:
            continue
        df["date"] = _reprt_to_date(df["bsns_year"], df["reprt_code"])
        df = df.dropna(subset=["date"])  # remove invalid rows
        # 계정명 표준화(핵심 항목 매핑) 후 피벗
        def _norm_account(name: str) -> str:
            s = str(name)
            if "당기순이익" in s or "분기순이익" in s or "(손실)" in s:
                return "net_income"
            if "자본총계" in s:
                return "equity"
            if "자산총계" in s:
                return "assets"
            return _slugify(s)

        values = df[["date", "account_nm", "thstrm_amount"]].rename(columns={"thstrm_amount": "value"})
        values["value"] = pd.to_numeric(values["value"].astype(str).str.replace(",", ""), errors="coerce")
        values["account_key"] = values["account_nm"].map(_norm_account)
        pivot = values.pivot_table(index="date", columns="account_key", values="value", aggfunc="last")
        pivot.columns = [f"fund_{col}" for col in pivot.columns]
        # 분기 금액 보정 및 계정 재매핑(당기-전기누계 차분)  # 한글 주석
        try:
            for col_name in ("thstrm_amount", "frmtrm_amount"):
                if col_name in df.columns:
                    df[col_name] = pd.to_numeric(df[col_name].astype(str).str.replace(",", ""), errors="coerce")
            def _ak(row: pd.Series) -> object:
                acc_id = str(row.get("account_id") or "").lower()
                if acc_id:
                    if "profitloss" in acc_id:
                        return "net_income"
                    if "totalassets" in acc_id:
                        return "assets"
                    if "totalequity" in acc_id or acc_id.endswith("equity"):
                        return "equity"
                    if "currentassets" in acc_id:
                        return "current_assets"
                    if "currentliabilities" in acc_id:
                        return "current_liabilities"
                    if "liabilities" in acc_id and "current" not in acc_id:
                        return "liabilities"
                    if "inventor" in acc_id:
                        return "inventories"
                name_c = str(row.get("account_nm") or "").replace(" ", "")
                if "당기순이익" in name_c or "분기순이익" in name_c or "순이익" in name_c:
                    return "net_income"
                if "자산총계" in name_c:
                    return "assets"
                if "부채총계" in name_c:
                    return "liabilities"
                if "자본총계" in name_c or "총자본" in name_c:
                    return "equity"
                if "유동자산" in name_c:
                    return "current_assets"
                if "유동부채" in name_c:
                    return "current_liabilities"
                if "재고자산" in name_c:
                    return "inventories"
                return None
            df["_ak"] = df.apply(_ak, axis=1)
            df_q = df.dropna(subset=["_ak"]).copy()
            if not df_q.empty:
                def _qv(r: pd.Series) -> float:
                    th = r.get("thstrm_amount"); fr = r.get("frmtrm_amount")
                    try:
                        thf = float(th) if pd.notna(th) else np.nan
                        frf = float(fr) if pd.notna(fr) else np.nan
                        return thf - frf if pd.notna(thf) and pd.notna(frf) else thf
                    except Exception:
                        return np.nan
                df_q["_val"] = df_q.apply(_qv, axis=1)
                pv2 = df_q[["date", "_ak", "_val"]].rename(columns={"_ak": "account_key", "_val": "value"})
                pv2 = pv2.pivot_table(index="date", columns="account_key", values="value", aggfunc="last")
                for col in pv2.columns:
                    pivot[f"fund_{col}"] = pv2[col]
        except Exception:
            pass
        # 추가 보강: 한국어 계정명을 직접 스캔해 핵심 항목을 채운다
        try:
            df_names = df.copy()
            df_names["account_nm"] = df_names["account_nm"].astype(str).str.replace(" ", "", regex=False)
            df_names["value"] = pd.to_numeric(df_names["thstrm_amount"].astype(str).str.replace(",", ""), errors="coerce")
            enrich_map = {
                "current_assets": ["유동자산"],
                "current_liabilities": ["유동부채"],
                "inventories": ["재고자산"],
                "liabilities": ["부채총계", "총부채"],
                "assets": ["자산총계", "총자산"],
                "equity": ["자본총계", "총자본", "지배기업의소유주지분"],
                "net_income": ["당기순이익", "분기순이익", "연결당기순이익"],
            }
            for key, names in enrich_map.items():
                mask = df_names["account_nm"].apply(lambda x: any(n in x for n in names))
                if not mask.any():
                    continue
                sel = df_names.loc[mask, ["date", "value"]].dropna()
                if sel.empty:
                    continue
                agg = sel.groupby("date")["value"].last()
                col = f"fund_{key}"
                if col not in pivot.columns:
                    pivot[col] = np.nan
                for d, v in agg.items():
                    pivot.loc[d, col] = v
        except Exception:
            pass
        frames.append(pivot)
    if not frames:
        return None

    merged = pd.concat(frames, axis=0).sort_index()
    merged.index = pd.to_datetime(merged.index)
    merged = merged.groupby(level=0).last().sort_index()
    # TTM 순이익(최근 4개 분기 합계)
    if "fund_net_income" in merged.columns:
        merged["fund_net_income_ttm"] = merged["fund_net_income"].rolling(window=4, min_periods=1).sum()
        _ni_tmp = merged["fund_net_income"].astype(float)
        _cnt = _ni_tmp.notna().astype(int).rolling(window=4, min_periods=1).sum()
        merged["fund_ttm_count"] = _cnt
        merged["fund_ttm_coverage"] = (_cnt / 4.0).astype(float)
    return merged


def _load_fundamentals2(ticker: str, config: MergeConfig) -> Optional[pd.DataFrame]:
    """멀티/단일 계정 JSON을 모두 읽어 결합한 재무 프레임을 반환한다.

    - 단일 계정(Single) 값이 있을 경우 우선 사용
    - 멀티 계정(Multi)은 보조로 사용
    - corp_code 매핑이 가능하면 해당 회사 디렉터리만 사용
    """
    root = config.fundamentals_dir or config.raw_root / "dart"
    roots = [root]
    try:
        alt = _find_project_root() / "Python" / "data" / "raw" / "dart"
        if alt.exists():
            roots.append(alt)
    except Exception:
        pass

    files_multi: list[Path] = []
    files_single: list[Path] = []
    for r in roots:
        if r.exists():
            files_multi.extend(r.glob("*/fnlttMultiAcnt_*.json"))
            files_single.extend(r.glob("*/fnlttSinglAcntAll_*.json"))

    # corp_code 필터링(가능 시)
    try:
        def _base(code: str) -> str:
            digits = "".join(ch for ch in str(code).strip() if ch.isdigit())
            if not digits:
                return str(code).zfill(6)
            d = digits.zfill(6)
            return d[:-1] + '0'
        base_ticker = _base(ticker)
        expected_corp: str | None = None
        csv_path = _find_project_root() / "data" / "dart_corpcode.csv"
        if csv_path.exists():
            import csv as _csv
            with csv_path.open("r", encoding="utf-8") as fp:
                rdr = _csv.DictReader(fp)
                headers = {h.lower(): h for h in (rdr.fieldnames or [])}
                t_col = headers.get("ticker") or headers.get("stock_code") or headers.get("code") or headers.get("symbol")
                c_col = headers.get("corp_code") or headers.get("corpcode") or headers.get("corpcode_id") or headers.get("corp")
                if t_col and c_col:
                    for row in rdr:
                        t = _base(row.get(t_col, ""))
                        c = str(row.get(c_col, "")).strip()
                        if t == base_ticker and c:
                            expected_corp = c
                            break
        if expected_corp:
            files_multi = [p for p in files_multi if p.parent.name == expected_corp]
            files_single = [p for p in files_single if p.parent.name == expected_corp]
    except Exception:
        pass

    frames_multi: list[pd.DataFrame] = []
    for path in files_multi:
        try:
            f = _parse_dart_multi(path, ticker)
            if f is not None and not f.empty:
                frames_multi.append(f)
        except Exception:
            continue

    frames_single: list[pd.DataFrame] = []
    for path in files_single:
        try:
            f = _parse_dart_single(path, ticker)
            if f is not None and not f.empty:
                frames_single.append(f)
        except Exception:
            continue

    df_multi = None
    if frames_multi:
        df_multi = pd.concat(frames_multi, axis=0).sort_index()
        df_multi = df_multi.groupby(level=0).last()

    df_single = None
    if frames_single:
        df_single = pd.concat(frames_single, axis=0).sort_index()
        df_single = df_single.groupby(level=0).last()

    if df_single is not None and df_multi is not None:
        return df_single.combine_first(df_multi)
    if df_single is not None:
        return df_single
    if df_multi is not None:
        return df_multi
    return None


def _parse_dart_single(path: Path, ticker: str) -> Optional[pd.DataFrame]:
    """fnlttSinglAcntAll JSON을 account_id/계정명으로 매핑하여 pivot 반환."""
    payload = _read_json(path)
    if not isinstance(payload, list):
        return None

    frames: list[pd.DataFrame] = []
    for entry in payload:
        rows = entry.get("rows", [])
        if not rows:
            continue
        df = pd.DataFrame(rows)
        # stock_code를 보통주 코드로 정규화하여 비교
        def _base(code: object) -> str:
            raw = str(code or "").strip()
            digits = "".join(ch for ch in raw if ch.isdigit())
            if not digits:
                return raw.zfill(6)
            d = digits.zfill(6)
            return d[:-1] + '0'
        if "stock_code" in df.columns:
            try:
                if df["stock_code"].notna().any():
                    codes = df["stock_code"].astype(str).map(_base).unique()
                    if _base(ticker) not in codes:
                        continue
            except Exception:
                pass
        if "account_nm" not in df.columns or "thstrm_amount" not in df.columns:
            continue
        df["date"] = _reprt_to_date(df.get("bsns_year"), df.get("reprt_code"))
        df = df.dropna(subset=["date"])  # remove invalid rows
        for col in ("thstrm_amount", "frmtrm_amount"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

        def _account_key_id(row: pd.Series) -> Optional[str]:
            acc_id = str(row.get("account_id") or "").lower()
            if acc_id:
                if "profitloss" in acc_id:
                    return "net_income"
                if "totalassets" in acc_id:
                    return "assets"
                if "totalequity" in acc_id or acc_id.endswith("equity"):
                    return "equity"
                if "currentassets" in acc_id:
                    return "current_assets"
                if "currentliabilities" in acc_id:
                    return "current_liabilities"
                if "liabilities" in acc_id and "current" not in acc_id:
                    return "liabilities"
                if "inventor" in acc_id:
                    return "inventories"
            # account_id가 없을 때 한글 계정명으로 보조
            name_c = str(row.get("account_nm") or "").replace(" ", "")
            if "당기순이익" in name_c or "분기순이익" in name_c or "순이익" in name_c:
                return "net_income"
            if "자산총계" in name_c:
                return "assets"
            if "부채총계" in name_c:
                return "liabilities"
            if "자본총계" in name_c or "총자본" in name_c:
                return "equity"
            if "유동자산" in name_c:
                return "current_assets"
            if "유동부채" in name_c:
                return "current_liabilities"
            if "재고자산" in name_c:
                return "inventories"
            return None

        df["account_key"] = df.apply(_account_key_id, axis=1)
        df = df.dropna(subset=["account_key"])  # 관심 계정만 유지

        def _quarter_value(row: pd.Series) -> float:
            th = row.get("thstrm_amount"); fr = row.get("frmtrm_amount")
            try:
                thf = float(th) if pd.notna(th) else np.nan
                frf = float(fr) if pd.notna(fr) else np.nan
                if pd.notna(thf) and pd.notna(frf):
                    return thf - frf
                return thf
            except Exception:
                return np.nan

        df["value_q"] = df.apply(_quarter_value, axis=1)
        values = df[["date", "account_key", "value_q"]].rename(columns={"value_q": "value"})
        pivot = values.pivot_table(index="date", columns="account_key", values="value", aggfunc="last")
        pivot.columns = [f"fund_{col}" for col in pivot.columns]
        frames.append(pivot)

    if not frames:
        return None

    merged = pd.concat(frames, axis=0).sort_index()
    merged.index = pd.to_datetime(merged.index)
    merged = merged.groupby(level=0).last().sort_index()
    return merged


def _load_news_features(ticker: str, config: MergeConfig) -> Optional[pd.DataFrame]:
    """뉴스 JSON/CSV/Parquet를 집계해 기사 건수·감성 평균을 만들다."""

    directory = config.news_dir or config.raw_root / "news" / ticker
    if not directory.exists():
        # 뉴스 폴더가 없어도 sentiment_report.json을 통해 감성 피처를 생성할 수 있으므로 아래에서 추가 시도  # 한글 주석
        pass

    frames: list[pd.DataFrame] = []
    for path in directory.glob("**/*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".json":
            rows = _read_json(path)
            if isinstance(rows, dict):
                rows = rows.get("items") or rows.get("data") or rows.get("articles") or []
            if not rows:
                continue
            df = pd.DataFrame(rows)
        elif suffix == ".csv":
            df = pd.read_csv(path)
        elif suffix == ".parquet":
            df = pd.read_parquet(path)
        else:
            continue
        if df.empty:
            continue
        date_col = next((col for col in ("date", "published_at", "created_at") if col in df.columns), None)
        if date_col is None:
            continue
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])
        df["date"] = df[date_col].dt.normalize()
        agg_kwargs = {"news_count": ("date", "count")}
        if "sentiment" in df.columns:
            agg_kwargs["news_sentiment_mean"] = ("sentiment", "mean")
        grouped = df.groupby("date").agg(**agg_kwargs)
        frames.append(grouped)
    # 추가: 데이터 루트의 sentiment_report.json에서 감성 집계 병합 시도  # 한글 주석
    try:
        report_path = config.raw_root / "sentiment_report.json"
        if report_path.exists():
            payload = _read_json(report_path)
            rows = payload if isinstance(payload, list) else (
                payload.get("items")
                or payload.get("data")
                or payload.get("rows")
                or payload.get("result")
                or []
            )
            selected: list[dict] = []
            for item in (rows or []):
                try:
                    code = str(item.get("stockCode") or item.get("ticker") or item.get("code") or "").zfill(6)
                    if code != ticker:
                        continue
                    raw_date = str(item.get("analysisDate") or item.get("date") or "").split(" ")[0]
                    dt = pd.to_datetime(raw_date, errors="coerce")
                    if pd.isna(dt):
                        continue
                    dt = dt.normalize()
                    sa = item.get("sentimentAnalysis") or {}
                    avg = sa.get("averageScore")
                    dist = sa.get("sentimentDistribution") or {}
                    pos = dist.get("positive")
                    neu = dist.get("neutral")
                    neg = dist.get("negative")
                    try:
                        total = float((pos or 0) + (neu or 0) + (neg or 0))
                    except Exception:
                        total = None
                    selected.append({
                        "date": dt,
                        "news_sentiment_mean": avg,
                        "news_count": total,
                        "news_pos": pos,
                        "news_neu": neu,
                        "news_neg": neg,
                    })
                except Exception:
                    continue
            if selected:
                sdf = pd.DataFrame(selected).dropna(subset=["date"]) 
                grouped = sdf.groupby("date").agg(
                    news_sentiment_mean=("news_sentiment_mean", "mean"),
                    news_count=("news_count", "sum"),
                    news_pos=("news_pos", "sum"),
                    news_neu=("news_neu", "sum"),
                    news_neg=("news_neg", "sum"),
                )
                frames.append(grouped)
    except Exception:
        pass
    if not frames:
        return None

    merged = pd.concat(frames, axis=0)
    news_count = merged.groupby(level=0)["news_count"].sum(min_count=1)
    sentiment = None
    if "news_sentiment_mean" in merged.columns:
        sentiment = merged.groupby(level=0)["news_sentiment_mean"].mean()
    # 감성 분포(양/중립/음) 합계가 존재하면 함께 포함한다.  # 한글 주석
    pos = merged["news_pos"].groupby(level=0).sum(min_count=1) if "news_pos" in merged.columns else None
    neu = merged["news_neu"].groupby(level=0).sum(min_count=1) if "news_neu" in merged.columns else None
    neg = merged["news_neg"].groupby(level=0).sum(min_count=1) if "news_neg" in merged.columns else None
    result = pd.DataFrame({"news_count": news_count})
    if sentiment is not None:
        result["news_sentiment_mean"] = sentiment
    if pos is not None:
        result["news_pos"] = pos
    if neu is not None:
        result["news_neu"] = neu
    if neg is not None:
        result["news_neg"] = neg
    result.index = pd.to_datetime(result.index)
    return result.sort_index()


def _fill_calendar_and_missing(df: pd.DataFrame) -> pd.DataFrame:
    """영업일 캘린더로 재인덱싱하고 결측값을 보정한다."""

    df = df.sort_index()
    calendar = pd.date_range(df.index.min(), df.index.max(), freq="B")
    df = df.reindex(calendar)
    df["is_trading_day"] = ~df["open"].isna()

    numeric_cols = df.select_dtypes(include="number").columns
    df[numeric_cols] = df[numeric_cols].ffill()
    if "volume" in df.columns:
        df["volume"] = df["volume"].fillna(0)
    if "tr_value" in df.columns:
        df["tr_value"] = df["tr_value"].fillna(0)
    df["is_trading_day"] = df["is_trading_day"].fillna(False)
    return df


def _reprt_to_date(year_series: pd.Series, code_series: pd.Series) -> pd.Series:
    """보고서 코드(11011 등)를 분기 마감일로 변환한다."""

    mapping = {
        "11013": (3, 31),  # Q1
        "11012": (6, 30),  # Half-year
        "11014": (9, 30),  # Q3
        "11011": (12, 31),  # FY
    }
    dates = []
    for year, code in zip(year_series.astype(str), code_series.astype(str)):
        month_day = mapping.get(code)
        if month_day is None:
            dates.append(pd.NaT)
            continue
        month, day = month_day
        try:
            dates.append(pd.Timestamp(int(year), month, day))
        except Exception:
            dates.append(pd.NaT)
    return pd.Series(dates)


def _latest_file(directory: Path, prefix: str) -> Optional[Path]:
    """가장 최신 파일(사전 정렬) 반환."""

    candidates = sorted(directory.glob(f"{prefix}*.json"))
    if not candidates:
        return None
    return candidates[-1]


def _read_json_table(path: Path) -> pd.DataFrame:
    """JSON 구조에서 리스트 부분을 찾아 DataFrame으로 변환."""

    payload = _read_json(path)
    data = None
    if isinstance(payload, dict):
        for key in ("data", "rows", "items", "result", "response"):
            if key in payload and isinstance(payload[key], list):
                data = payload[key]
                break
        if data is None:
            for value in payload.values():
                if isinstance(value, list):
                    data = value
                    break
    else:
        data = payload
    if data is None:
        raise ValueError(f"Unexpected JSON table format: {path}")
    df = pd.DataFrame(data)
    if "date" not in df.columns and df.columns.size:
        first = df.columns[0]
        df.rename(columns={first: "date"}, inplace=True)
    return df


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _slugify(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")


def _resolve_raw_root(raw_root: str | Path | None) -> Path:
    if raw_root is not None:
        return Path(raw_root)
    return _find_project_root() / "data" / "raw"


def _resolve_bronze_root(bronze_root: str | Path | None) -> Path:
    if bronze_root is not None:
        return Path(bronze_root)
    return _find_project_root() / "data" / "bronze"


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists():
            return parent
    for parent in current.parents:
        if (parent / "data").exists():
            return parent
    return current.parents[4]


def _discover_raw_tickers(raw_root: Path, price_source: str) -> list[str]:
    """raw 디렉터리 구조에서 가능한 티커명을 자동으로 수집한다."""
    price_source = price_source.lower()
    candidates: set[str] = set()
    sources: list[Path] = []
    if price_source in ("pykrx", "both") or price_source not in ("pykrx", "kiwoom"):
        sources.append(raw_root / "pykrx")
    if price_source in ("kiwoom", "both"):
        sources.append(raw_root / "kiwoom")
    for src in sources:
        if src.exists():
            for child in src.iterdir():
                if child.is_dir():
                    candidates.add(child.name)
    return sorted(candidates)


def _write_table(df: pd.DataFrame, path: Path) -> Path:
    """Parquet 엔진이 없을 경우 자동으로 pickle로 대체 저장한다."""
    try:
        df.to_parquet(path, index=False)
        return path
    except (ImportError, ValueError):
        fallback = path.with_suffix('.pkl')
        df.to_pickle(fallback)
        LOGGER.warning('pyarrow/fastparquet 미설치로 pickle로 저장합니다: %s', fallback)
        return fallback
