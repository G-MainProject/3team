# -*- coding: utf-8 -*-
"""Feature engineering utilities for the silver layer."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional, Set

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

# 기본 이동 창 설정 (가격/거래량 파생 계산에 활용)
DEFAULT_WINDOWS = (5, 10, 20, 60, 120)


# 브론즈 데이터를 읽어 기술적 지표를 생성하고 실버 계층에 저장

def run(
    *,
    tickers: Iterable[str] | None = None,
    bronze_root: str | Path | None = None,
    silver_root: str | Path | None = None,
    windows: Iterable[int] = DEFAULT_WINDOWS,
) -> list[Path]:
    """Compute features for ``tickers`` and persist into the silver layer."""

    bronze_dir = _resolve_bronze_root(bronze_root)
    silver_dir = _resolve_silver_root(silver_root)
    silver_dir.mkdir(parents=True, exist_ok=True)
    # settings.yaml에 price_windows가 있으면 덮어쓴다
    try:
        cfg_windows = _load_price_windows_from_settings()
        if cfg_windows:
            windows = tuple(cfg_windows)
    except Exception:
        pass

    targets = list(tickers) if tickers else _discover_tickers(bronze_dir)
    # ETF 식별 집합 로드(가능하면 pykrx 사용, 실패 시 빈 집합)
    try:
        etf_set = _load_etf_ticker_set()
    except Exception:
        etf_set = set()
    outputs: list[Path] = []
    for ticker in targets:
        bronze_path = _load_bronze_path(bronze_dir, ticker)
        if bronze_path is None:
            LOGGER.warning("Bronze dataset missing for %s", ticker)
            continue
        df = _read_table(bronze_path)
        if df.empty:
            LOGGER.warning("Bronze dataset empty for %s", ticker)
            continue
        # is_etf 플래그 주입(모델이 타입 차이를 인지하도록)
        is_etf = _is_etf_ticker(ticker, etf_set)
        enriched = _build_features(df, windows, is_etf=is_etf)
        target = silver_dir / f"{ticker}.parquet"
        output_path = _write_table(enriched, target)
        outputs.append(output_path)
        LOGGER.info("Silver dataset saved: %s", output_path)
    return outputs


# ---------------------------------------------------------------------------
# 지표 계산 함수
# ---------------------------------------------------------------------------

def _build_features(df: pd.DataFrame, windows: Iterable[int], *, is_etf: bool = False) -> pd.DataFrame:
    """가격/거래량 기반 지표를 계산하고 결측을 보정한다."""

    df = df.copy()
    # 타입 플래그(ETF=1, 기업=0)
    try:
        df["is_etf"] = 1.0 if is_etf else 0.0
    except Exception:
        pass
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    for col in ("open", "high", "low", "close", "volume"):
        if col not in df.columns:
            df[col] = np.nan
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)

    df = _add_price_windows(df, windows)
    df = _add_macd(df)
    df = _add_rsi(df)
    # 추가 기술지표: Bollinger Bands, OBV (기본값 적용)
    df = _add_bollinger(df, window=20, k=2.0)
    df = _add_obv(df, ema_window=10)
    df = _add_dmi(df)
    df = _add_vr(df)
    df = _add_vma(df, windows)
    df = _add_psychological_line(df)
    df = _add_atr(df)
    df = _add_envelope(df)

    # 계산 과정에서 생길 수 있는 ±inf/NaN 처리
    # 간단 재무 파생: EPS/BPS가 있으면 ROE(근사) = EPS/BPS
    if "eps" in df.columns and "bps" in df.columns:
        with np.errstate(divide="ignore", invalid="ignore"):
            df["roe"] = (df["eps"].astype(float) / df["bps"].astype(float)).replace([np.inf, -np.inf], np.nan)
    # 한국어 주석: 뉴스 지표는 결측을 0으로 강제하지 않고 NaN을 유지한다.
    numeric_cols = df.select_dtypes(include=["number", "bool"]).columns
    news_cols = [c for c in numeric_cols if str(c).startswith("news_")]
    other_cols = [c for c in numeric_cols if c not in news_cols]
    if other_cols:
        df[other_cols] = df[other_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if news_cols:
        df[news_cols] = df[news_cols].replace([np.inf, -np.inf], np.nan)
    return df


def _add_price_windows(df: pd.DataFrame, windows: Iterable[int]) -> pd.DataFrame:
    """이동평균, 표준편차, ROC 등 기본 추세 지표."""

    close = df["close"]
    for window in windows:
        df[f"ma_{window}"] = close.rolling(window, min_periods=1).mean()
        df[f"std_{window}"] = close.rolling(window, min_periods=1).std(ddof=0)
        df[f"roc_{window}"] = close.pct_change(window)
    return df


def _add_macd(df: pd.DataFrame) -> pd.DataFrame:
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    return df


def _add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi"] = df["rsi"].bfill().fillna(50)
    return df


def _add_dmi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Directional Movement Index + ADX."""

    up_move = df["high"].diff()
    down_move = df["low"].diff() * -1
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    tr = _true_range(df)
    atr = tr.rolling(period, min_periods=period).mean().replace(0, np.nan)
    plus_di = 100 * plus_dm.rolling(period, min_periods=period).sum() / (atr * period)
    minus_di = 100 * minus_dm.rolling(period, min_periods=period).sum() / (atr * period)
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    df["dmi_plus"] = plus_di.fillna(0)
    df["dmi_minus"] = minus_di.fillna(0)
    df["adx"] = dx.rolling(period, min_periods=period).mean().fillna(0)
    return df


def _add_vr(df: pd.DataFrame, period: int = 26) -> pd.DataFrame:
    """VR(Volume Ratio) 지표."""

    close = df["close"]
    prev_close = close.shift(1)
    volume = df["volume"]
    up_vol = volume.where(close > prev_close, 0.0)
    down_vol = volume.where(close < prev_close, 0.0)
    same_vol = volume.where(close == prev_close, 0.0)
    numerator = up_vol.rolling(period, min_periods=period).sum() + same_vol.rolling(period, min_periods=period).sum() / 2
    denominator = down_vol.rolling(period, min_periods=period).sum() + same_vol.rolling(period, min_periods=period).sum() / 2
    df["vr"] = (numerator / denominator.replace(0, np.nan)).fillna(1.0)
    return df


def _add_vma(df: pd.DataFrame, windows: Iterable[int]) -> pd.DataFrame:
    volume = df["volume"]
    for window in windows:
        df[f"vma_{window}"] = volume.rolling(window, min_periods=1).mean()
    return df


def _add_psychological_line(df: pd.DataFrame, period: int = 12) -> pd.DataFrame:
    diff = df["close"].diff()
    up_days = (diff > 0).astype(int)
    df["psychological_line"] = up_days.rolling(period, min_periods=1).mean() * 100
    return df


def _add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    tr = _true_range(df)
    df["atr"] = tr.rolling(period, min_periods=period).mean().fillna(0)
    return df


def _add_envelope(df: pd.DataFrame, window: int = 20, pct: float = 0.05) -> pd.DataFrame:
    ma = df["close"].rolling(window, min_periods=1).mean()
    df["envelope_upper"] = ma * (1 + pct)
    df["envelope_lower"] = ma * (1 - pct)
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    """고저갭·전일 종가 대비 변동 폭을 고려한 TR 계산."""

    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    return pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).fillna(0)

def _load_price_windows_from_settings() -> list[int] | None:
    try:
        root = _find_project_root()
        cfg = root / "Python" / "pipeline" / "config" / "settings.yaml"
        if not cfg.exists() or yaml is None:
            return None
        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        feats = data.get("features") or {}
        pws = feats.get("price_windows")
        if isinstance(pws, list):
            return [int(x) for x in pws]
        return None
    except Exception:
        return None


def _add_bollinger(df: pd.DataFrame, *, window: int = 20, k: float = 2.0) -> pd.DataFrame:
    ma = df["close"].rolling(window, min_periods=1).mean()
    sd = df["close"].rolling(window, min_periods=1).std(ddof=0)
    df["bb_mid"] = ma
    df["bb_upper"] = ma + k * sd
    df["bb_lower"] = ma - k * sd
    denom = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    df["bb_bandwidth"] = (df["bb_upper"] - df["bb_lower"]) / (df["bb_mid"].replace(0, np.nan)).abs()
    df["bb_percent_b"] = (df["close"] - df["bb_lower"]) / denom
    return df


def _add_obv(df: pd.DataFrame, *, ema_window: int = 10) -> pd.DataFrame:
    close = df["close"].astype(float)
    volume = df["volume"].fillna(0).astype(float)
    direction = np.sign(close.diff().fillna(0))
    obv = (direction * volume).cumsum()
    df["obv"] = obv
    df["obv_ema"] = obv.ewm(span=ema_window, adjust=False).mean()
    return df


# ---------------------------------------------------------------------------
# 경로/탐색 헬퍼
# ---------------------------------------------------------------------------

def _discover_tickers(bronze_dir: Path) -> list[str]:
    return sorted({p.stem for p in bronze_dir.glob('*.parquet')} | {p.stem for p in bronze_dir.glob('*.pkl')})


def _resolve_bronze_root(bronze_root: str | Path | None) -> Path:
    if bronze_root is not None:
        return Path(bronze_root)
    return _find_project_root() / "data" / "bronze"


def _resolve_silver_root(silver_root: str | Path | None) -> Path:
    if silver_root is not None:
        return Path(silver_root)
    return _find_project_root() / "data" / "silver"


def _load_etf_ticker_set() -> Set[str]:
    """pykrx에서 ETF 티커 집합을 로드(실패 시 빈 집합).

    KRX 형식 6자리 문자열로 반환.
    """
    tickers: Set[str] = set()
    try:
        from pykrx import stock  # type: ignore
        lst = stock.get_etf_ticker_list()
        for t in lst:
            s = str(t).strip()
            if s:
                digits = ''.join(ch for ch in s if ch.isdigit())
                tickers.add(digits.zfill(6) if digits else s)
    except Exception:
        pass
    return tickers


def _is_etf_ticker(ticker: str, etf_set: Set[str]) -> bool:
    raw = str(ticker or "").strip()
    digits = ''.join(ch for ch in raw if ch.isdigit())
    key = digits.zfill(6) if digits else raw.zfill(6)
    return key in etf_set


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists():
            return parent
    for parent in current.parents:
        if (parent / "data").exists():
            return parent
    return current.parents[4]

def _load_bronze_path(bronze_dir: Path, ticker: str) -> Path | None:
    for suffix in ('.parquet', '.pkl'):
        candidate = bronze_dir / f"{ticker}{suffix}"
        if candidate.exists():
            return candidate
    return None


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix == '.parquet':
        return pd.read_parquet(path)
    if path.suffix == '.pkl':
        return pd.read_pickle(path)
    raise ValueError(f'Unsupported file format: {path}')


def _write_table(df: pd.DataFrame, path: Path) -> Path:
    try:
        df.to_parquet(path, index=False)
        return path
    except (ImportError, ValueError):
        fallback = path.with_suffix('.pkl')
        df.to_pickle(fallback)
        LOGGER.warning('pyarrow/fastparquet 미설치로 pickle로 저장합니다: %s', fallback)
        return fallback
