"""Dataset construction utilities for the gold layer."""

from __future__ import annotations

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

    X, y = _assemble_sequences(cfg, tickers)
    if X.size == 0:
        raise RuntimeError("No samples collected from silver datasets.")

    splits = _split_indices(len(y), cfg.split)

    scaler = StandardScaler()
    train_idx = splits["train"]
    if train_idx.size == 0:
        raise RuntimeError("Training split is empty. Adjust split ratios or sequence length.")
    X_train = X[train_idx]
    scaler.fit(X_train.reshape(X_train.shape[0], -1))

    datasets: dict[str, Path] = {}
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
        datasets[split_name] = x_path
        LOGGER.info("Saved %s split: %s (%d samples)", split_name, x_path, y_split.shape[0])

    scaler_path = cfg.artifacts_root / "models" / "scaler.pkl"
    scaler_path.write_bytes(pickle.dumps(scaler))
    LOGGER.info("Scaler persisted to %s", scaler_path)
    return datasets


def _assemble_sequences(cfg: DatasetConfig, tickers: Iterable[str] | None) -> tuple[np.ndarray, np.ndarray]:
    files = sorted(cfg.silver_root.glob("*.parquet")) + sorted(cfg.silver_root.glob("*.pkl"))
    if tickers:
        tickers = {ticker for ticker in tickers}
        files = [file for file in files if file.stem in tickers]

    X_list: list[np.ndarray] = []
    y_list: list[np.ndarray] = []
    seq_len = cfg.sequence_length
    horizons = cfg.horizons
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

        valid_mask = ~np.isnan(target_matrix).any(axis=1)
        valid_mask[: seq_len - 1] = False  # 시작 부분 윈도우 부족 제거
        feature_array = feature_frame.to_numpy(dtype=float)[valid_mask]
        target_array = target_matrix[valid_mask]

        if feature_array.shape[0] < seq_len:
            continue

        for idx in range(seq_len - 1, feature_array.shape[0]):
            window = feature_array[idx - seq_len + 1 : idx + 1]
            if window.shape[0] != seq_len:
                continue
            X_list.append(window)
            y_list.append(target_array[idx])

    if not X_list:
        return np.empty((0, seq_len, 0)), np.empty((0, len(horizons)))

    X = np.stack(X_list)
    y = np.stack(y_list)
    return X, y


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
