"""
수동 라벨링된 기사 문장을 기반으로 감성 사전 CSV(finance_data.csv)를 재구성하는 스크립트.
"""
import argparse
from pathlib import Path

import pandas as pd

VALID_LABELS = {"positive", "negative", "neutral"}
PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = PROJECT_DIR / "finance_data.csv"
DEFAULT_LABELED = REPO_ROOT / "data" / "labeled_corpus.csv"


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.rename(columns={c: c.strip().lower() for c in df.columns})
    if {"labels", "kor_sentence"} - set(df.columns):
        raise ValueError("CSV에는 'labels'와 'kor_sentence' 컬럼이 포함되어야 합니다.")

    df["labels"] = df["labels"].astype(str).str.strip().str.lower()
    df["kor_sentence"] = df["kor_sentence"].astype(str).str.strip()

    df = df[df["labels"].isin(VALID_LABELS)]
    df = df[df["kor_sentence"].str.len() > 5]  # 너무 짧은 문장은 제거
    df = df.drop_duplicates(subset=["labels", "kor_sentence"]).reset_index(drop=True)
    return df


def merge_existing(df: pd.DataFrame, existing_path: Path | None) -> pd.DataFrame:
    if existing_path and existing_path.exists():
        base_df = pd.read_csv(existing_path)
        base_df = normalize_dataframe(base_df)
        combined = pd.concat([base_df, df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["labels", "kor_sentence"])
        return combined.reset_index(drop=True)
    return df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="라벨링된 코퍼스로 finance_data.csv 감성 사전을 갱신"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_LABELED,
        help="라벨링된 코퍼스 CSV 경로 (기본: data/labeled_corpus.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="결과 감성 사전 CSV 경로 (기본: Python/Prediction/finance_data.csv)",
    )
    parser.add_argument(
        "--merge-existing",
        action="store_true",
        help="기존 finance_data.csv 내용과 병합한 뒤 저장",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {args.input}")

    labeled_df = pd.read_csv(args.input)
    labeled_df = normalize_dataframe(labeled_df)

    if labeled_df.empty:
        raise ValueError("라벨링된 데이터가 비어 있습니다. labels/kor_sentence를 확인하세요.")

    if args.merge_existing:
        labeled_df = merge_existing(labeled_df, args.output if args.output.exists() else None)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    labeled_df.to_csv(args.output, index=False, encoding="utf-8")

    label_counts = labeled_df["labels"].value_counts().to_dict()
    print(f"총 {len(labeled_df)}개 문장을 '{args.output}'에 저장했습니다.")
    print(f"라벨 분포: {label_counts}")


if __name__ == "__main__":
    main()

