# -*- coding: utf-8 -*-
"""Dataset construction utilities for the gold layer."""

from __future__ import annotations

import json
import os  # 동적 horizon 환경변수 사용
import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd


try:  # Optional dependency for YAML configs
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fallback when PyYAML is unavailable
    yaml = None

LOGGER = logging.getLogger(__name__)


class StandardScaler:
    """Lightweight replacement for ``sklearn.preprocessing.StandardScaler``."""

    def __init__(self) -> None:
        self.mean_: np.ndarray | None = None
        self.scale_: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> "StandardScaler":
        self.mean_ = X.mean(axis=0)
        self.scale_ = X.std(axis=0)
        self.scale_[self.scale_ == 0] = 1.0
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.scale_ is None:
            raise RuntimeError("Scaler has not been fitted.")
        return (X - self.mean_) / self.scale_

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)


@dataclass(slots=True)
class DatasetConfig:
    silver_root: Path
    gold_root: Path
    artifacts_root: Path
    label_threshold: float
    sequence_length: int
    horizons: list[int]
    split: Mapping[str, float]

    def __post_init__(self) -> None:
        total = sum(self.split.values())
        if not np.isclose(total, 1.0):
            self.split = {k: v / total for k, v in self.split.items()}
        self.horizons = [int(h) for h in self.horizons]


def run(
    *,
    silver_root: str | Path | None = None,
    gold_root: str | Path | None = None,
    artifacts_root: str | Path | None = None,
    settings_path: str | Path | None = None,
    tickers: Iterable[str] | None = None,
) -> dict[str, Path]:
    cfg = _load_config(silver_root, gold_root, artifacts_root, settings_path)
    for split in ("train", "val", "test"):
        (cfg.gold_root / split).mkdir(parents=True, exist_ok=True)
    (cfg.artifacts_root / "models").mkdir(parents=True, exist_ok=True)

    X, y, labels, closes, used_horizons = _assemble_sequences(cfg, tickers)
    if X.size == 0:
        raise RuntimeError("No samples collected from silver datasets.")

    # 티커별로 최신 샘플이 test에 최소 1개 포함되도록 분할(시간 순서 보존)
    # 전체 비율(cfg.split)은 가급적 유지하되, 티커 단위 보장을 우선시한다.
    splits = _split_indices_grouped(labels, cfg.split)

    scaler = StandardScaler()
    train_idx = splits["train"]
    if train_idx.size == 0:
        raise RuntimeError("Training split is empty. Adjust split ratios or sequence length.")
    X_train = X[train_idx]
    scaler.fit(X_train.reshape(X_train.shape[0], -1))

    datasets: dict[str, Path] = {}
    # 동적으로 선택된 horizons를 고정 파일로 저장하여 s3/s4/s5와 일관성 유지
    try:
        horizons_path = cfg.gold_root / "horizons.json"
        horizons_path.write_text(json.dumps(list(map(int, used_horizons)), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    for split_name in ("train", "val", "test"):
        idx = splits[split_name]
        X_split = X[idx]
        y_split = y[idx]
        if X_split.size:
            scaled = scaler.transform(X_split.reshape(X_split.shape[0], -1)).reshape(X_split.shape)
        else:
            scaled = X_split
        split_dir = cfg.gold_root / split_name
        x_path = split_dir / "X.npy"
        y_path = split_dir / "y.npy"
        np.save(x_path, scaled)
        np.save(y_path, y_split)
        close_split = np.asarray([closes[int(i)] for i in idx.tolist()], dtype=float)
        close_path = split_dir / "close.npy"
        np.save(close_path, close_split)
        label_items = [labels[int(i)] for i in idx.tolist()]
        label_path = split_dir / "labels.json"
        label_path.write_text(json.dumps(label_items, ensure_ascii=False, indent=2), encoding="utf-8")
        datasets[split_name] = x_path
        LOGGER.info("Saved %s split: %s (%d samples)", split_name, x_path, y_split.shape[0])

    scaler_path = cfg.artifacts_root / "models" / "scaler.pkl"
    scaler_path.write_bytes(pickle.dumps(scaler))
    LOGGER.info("Scaler persisted to %s", scaler_path)
    return datasets


def _assemble_sequences(cfg: DatasetConfig, tickers: Iterable[str] | None) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]], np.ndarray, list[int]]:
    parquet_files = sorted(cfg.silver_root.glob("*.parquet"))
    pkl_files = sorted(cfg.silver_root.glob("*.pkl"))
    files = parquet_files if parquet_files else pkl_files
    if tickers:
        tickers = {ticker for ticker in tickers}
        files = [file for file in files if file.stem in tickers]

    # 모든 티커에서 동일한 feature 차원을 보장하기 위해 스키마를 먼저 수집한다.  # 한글 주석
    union_cols: set[str] = set()
    rows_per_file: dict[Path, int] = {}
    for file in files:
        try:
            df_probe = _read_table(file)
        except Exception:
            continue
        if df_probe is None or df_probe.empty:
            continue
        try:
            rows_per_file[file] = int(len(df_probe))
        except Exception:
            rows_per_file[file] = 0
        numeric_cols = df_probe.select_dtypes(include=[np.number, bool]).columns
        for col in numeric_cols:
            if col not in {"date", "ticker"}:
                union_cols.add(str(col))
    # 핵심 컬럼 순서를 먼저 고정(open, high, low, close, volume), 그 외는 알파벳 정렬  # 한글 주석
    primary = ["open", "high", "low", "close", "volume"]
    feature_order = [c for c in primary if c in union_cols] + sorted([c for c in union_cols if c not in primary])

    X_list: list[np.ndarray] = []
    y_list: list[np.ndarray] = []
    labels: list[dict[str, object]] = []
    closes_list: list[float] = []
    seq_len = cfg.sequence_length
    # 동적 horizon 선택: 가용 커버리지 기반으로 최대 horizon 축소
    base_horizons = sorted(int(h) for h in cfg.horizons)
    total_files = max(len(files), 1)
    # 최소 커버리지 비율(기본 0.8). 환경변수로 조정 가능
    try:
        min_cov = float(os.getenv("DYNAMIC_HORIZON_MIN_COVERAGE", "0.8"))
    except Exception:
        min_cov = 0.8
    # 각 후보 h에 대해 rows >= seq_len + h 를 만족하는 파일 비율 계산
    best_h: int | None = None
    for h in base_horizons:
        ok = 0
        need = seq_len + int(h)
        for f in files:
            n = rows_per_file.get(f)
            if n is None:
                # 파일을 다시 읽어 행수 계산
                try:
                    n = int(len(_read_table(f)))
                except Exception:
                    n = 0
                rows_per_file[f] = n
            if n >= need:
                ok += 1
        frac = ok / total_files if total_files else 0.0
        if frac >= min_cov:
            best_h = h
    if best_h is None:
        # 한 개 파일이라도 만들 수 있는 최소 horizon로 폴백
        for h in base_horizons:
            need = seq_len + int(h)
            if any(rows_per_file.get(f, 0) >= need for f in files):
                best_h = h
                break
    selected_horizons = [h for h in base_horizons if best_h is None or h <= int(best_h)]
    if not selected_horizons:
        selected_horizons = base_horizons[:1]
    # Optional override to force full horizon set (e.g., include 1y even with low coverage)
    force_full = os.getenv("FORCE_FULL_HORIZONS") or os.getenv("FORCE_1Y") or os.getenv("FORCE_HORIZONS")
    if force_full:
        horizons = base_horizons
    else:
        horizons = selected_horizons
    max_horizon = max(horizons)

    for file in files:
        df = _read_table(file)
        if df.empty or "close" not in df.columns:
            LOGGER.warning("Skipping silver file without close column: %s", file)
            continue
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df.sort_values("date", inplace=True)
            df.reset_index(drop=True, inplace=True)

        # 수집된 스키마 순서(feature_order)에 맞춰 컬럼을 재배치하고, 없는 컬럼은 0으로 채움  # 한글 주석
        if feature_order:
            # 모든 수치 컬럼 변환 후 스키마 적용
            numeric_df = df.select_dtypes(include=[np.number, bool]).astype(float)
            feature_frame = numeric_df.reindex(columns=feature_order).fillna(0.0)
        else:
            feature_cols = [col for col in df.columns if col not in {"date", "ticker"}]
            feature_frame = df[feature_cols].select_dtypes(include=[np.number, bool]).astype(float)
        if feature_frame.shape[1] == 0:
            LOGGER.warning("No numeric features in %s", file)
            continue

        close = df["close"].astype(float).to_numpy()
        targets = []
        for horizon in horizons:
            future = np.roll(close, -horizon)
            future[-horizon:] = np.nan
            returns = future / close - 1
            targets.append(returns)
        target_matrix = np.stack(targets, axis=1)
        clip_env = os.getenv("RETURN_CLIP_MAX")
        if clip_env:
            try:
                clip_val = float(clip_env)
            except Exception:
                clip_val = None
        else:
            clip_val = 0.3
        if clip_val and clip_val > 0:
            np.clip(target_matrix, -clip_val, clip_val, out=target_matrix)

        valid_mask = ~np.isnan(target_matrix).any(axis=1)
        valid_mask[: seq_len - 1] = False  # 시작 부분 윈도우 부족 제거
        feature_array = feature_frame.to_numpy(dtype=float)[valid_mask]
        target_array = target_matrix[valid_mask]

        if feature_array.shape[0] < seq_len:
            continue

        valid_indices = np.flatnonzero(valid_mask)

        for idx in range(seq_len - 1, feature_array.shape[0]):
            window = feature_array[idx - seq_len + 1 : idx + 1]
            if window.shape[0] != seq_len:
                continue
            X_list.append(window)
            y_list.append(target_array[idx])
            if valid_indices.size > idx:
                orig_idx = int(valid_indices[idx])
            else:
                orig_idx = idx
            close_value = float(close[orig_idx])
            label_entry = {"ticker": file.stem}
            if "date" in df.columns:
                date_value = df.iloc[orig_idx].get("date")
                if hasattr(date_value, "isoformat"):
                    date_value = date_value.isoformat()
                if date_value is not None:
                    label_entry["date"] = str(date_value)
            labels.append(label_entry)
            closes_list.append(close_value)

    if not X_list:
        return np.empty((0, seq_len, 0)), np.empty((0, len(horizons))), [], np.empty(0), horizons

    X = np.stack(X_list)
    y = np.stack(y_list)
    closes_array = np.asarray(closes_list, dtype=float) if closes_list else np.empty(0)
    return X, y, labels, closes_array, horizons


def _split_indices(sample_count: int, split: Mapping[str, float]) -> dict[str, np.ndarray]:
    train_size = int(sample_count * split.get("train", 0.7))
    val_size = int(sample_count * split.get("val", 0.15))
    test_size = sample_count - train_size - val_size
    indices = np.arange(sample_count)
    result = {
        "train": indices[:train_size],
        "val": indices[train_size : train_size + val_size],
        "test": indices[train_size + val_size : train_size + val_size + test_size],
    }
    return {k: v.copy() for k, v in result.items()}


def _split_indices_grouped(labels: list[dict[str, object]], split: Mapping[str, float]) -> dict[str, np.ndarray]:
    """티커별로 그룹핑하여 시간 순서를 보존한 분할을 수행한다.

    규칙
    - 각 티커의 마지막(최신) 샘플은 무조건 test에 포함
    - 남은 샘플은 train/val/test 비율에 맞춰 앞에서부터 순차 배치
    - 글로벌 비율과 약간의 오차는 허용(티커 보장을 우선)
    - 모든 티커가 샘플 1개뿐이면 train이 비게 될 수 있으므로, 그 경우에는
      기존 전역 분할(_split_indices)로 폴백한다.
    """
    import math

    train_ratio = float(split.get("train", 0.7))
    val_ratio = float(split.get("val", 0.15))
    # test_ratio = 1 - train - val (암묵적 계산)

    # 1) 티커별 인덱스 그룹핑(이미 라벨 순서는 시간 순서와 정렬되어 있음)
    groups: dict[str, list[int]] = {}
    for idx, item in enumerate(labels):
        ticker = str(item.get("ticker", ""))
        groups.setdefault(ticker, []).append(idx)

    train_idx: list[int] = []
    val_idx: list[int] = []
    test_idx: list[int] = []

    # 2) 각 그룹 내에서 분할 수행(마지막은 test 고정)
    for ticker, idxs in groups.items():
        if not idxs:
            continue
        if len(idxs) == 1:
            # 샘플이 1개면 test로만 보냄
            test_idx.append(idxs[0])
            continue
        # 최신 샘플(마지막)을 우선 test에 할당
        reserved_test = idxs[-1]
        remaining = idxs[:-1]

        if remaining:
            n = len(remaining)
            n_train = int(math.floor(n * train_ratio))
            n_val = int(math.floor(n * val_ratio))
            # 최소 1개는 train에 배치(가능한 경우)
            if n >= 2 and n_train == 0:
                n_train = 1
            # 슬라이싱 범위 보정
            n_train = min(n_train, n)
            n_val = min(n_val, max(0, n - n_train))

            train_part = remaining[:n_train]
            val_part = remaining[n_train:n_train + n_val]
            test_part = remaining[n_train + n_val:]

            train_idx.extend(train_part)
            val_idx.extend(val_part)
            test_idx.extend(test_part)

        test_idx.append(reserved_test)

    # 3) 폴백: train이 비면 전역 분할로 대체(학습 불가 방지)
    if len(train_idx) == 0:
        return _split_indices(len(labels), split)

    # 4) numpy 배열로 변환하여 반환
    return {
        "train": np.asarray(sorted(train_idx), dtype=int),
        "val": np.asarray(sorted(val_idx), dtype=int),
        "test": np.asarray(sorted(test_idx), dtype=int),
    }


def _load_config(
    silver_root: str | Path | None,
    gold_root: str | Path | None,
    artifacts_root: str | Path | None,
    settings_path: str | Path | None,
) -> DatasetConfig:
    root = _find_project_root()
    settings_file = Path(settings_path) if settings_path else root / "Python" / "pipeline" / "config" / "settings.yaml"
    config: dict = {}
    if settings_file.exists():
        raw_text = settings_file.read_text(encoding="utf-8")
        if yaml is not None:
            config = yaml.safe_load(raw_text) or {}
        else:
            config = _parse_yaml_like(raw_text)

    paths = config.get("paths", {})
    config_dir = settings_file.parent
    silver_dir = _resolve_path(silver_root, paths.get("silver"), root, config_dir, "data/silver")
    gold_dir = _resolve_path(gold_root, paths.get("gold"), root, config_dir, "data/gold")
    artifacts_dir = _resolve_path(artifacts_root, paths.get("artifacts"), root, config_dir, "Python/pipeline/artifacts")

    dataset_cfg = config.get("dataset", {})
    label_threshold = float(dataset_cfg.get("label_threshold", 0.0035))
    sequence_length = int(dataset_cfg.get("sequence_length", 30))
    split = dataset_cfg.get("split") or dataset_cfg.get("splits") or {"train": 0.7, "val": 0.15, "test": 0.15}
    horizons = dataset_cfg.get("horizons", [1, 5, 20, 120, 250])

    return DatasetConfig(
        silver_root=silver_dir,
        gold_root=gold_dir,
        artifacts_root=artifacts_dir,
        label_threshold=label_threshold,
        sequence_length=sequence_length,
        horizons=[int(h) for h in horizons],
        split=split,
    )


def _parse_yaml_like(text: str) -> dict:
    """Very small YAML reader supporting nested ``key: value`` blocks."""

    def cast(value: str):
        value = value.strip()
        if value in {"", "null", "None"}:
            return None
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip().strip('"\'') for item in value[1:-1].split(",") if item.strip()]
            parsed = []
            for item in items:
                try:
                    parsed.append(float(item) if "." in item else int(item))
                except ValueError:
                    parsed.append(item)
            return parsed
        return value.strip('"\'')

    root: dict = {}
    stack = [root]
    indent_stack = [0]
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        while indent < indent_stack[-1] and len(stack) > 1:
            stack.pop()
            indent_stack.pop()
        key, _, remainder = line.partition(":")
        key = key.strip()
        value = remainder.strip()
        if value:
            stack[-1][key] = cast(value)
        else:
            new_dict: dict = {}
            stack[-1][key] = new_dict
            stack.append(new_dict)
            indent_stack.append(indent + 2)
    return root


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists():
            return parent
    for parent in current.parents:
        if (parent / "data").exists():
            return parent
    return current.parents[4]


def _resolve_path(
    override: str | Path | None,
    configured: str | None,
    root: Path,
    config_dir: Path,
    default: str,
) -> Path:
    if override is not None:
        return Path(override).resolve()
    candidate = Path(configured) if configured else Path(default)
    if candidate.is_absolute():
        return candidate
    config_candidate = (config_dir / candidate).resolve()
    target_data_root = (root / Path("data")).resolve()
    if (config_candidate.exists() or config_candidate.parent.exists()) and target_data_root in config_candidate.parents:
        return config_candidate
    return (root / Path(default)).resolve()


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".pkl":
        return pd.read_pickle(path)
    raise ValueError(f"Unsupported file format: {path}")
