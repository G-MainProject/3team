"""
finance_sentiment_corpus 기반의 감성 사전을 이용해 뉴스 문장을 분석하는 모듈.
감성 사전 CSV는 positive/negative/neutral 라벨과 문장을 포함해야 한다.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, List, Tuple

import math

import pandas as pd
from konlpy.tag import Okt

POS_LABEL = "positive"
NEG_LABEL = "negative"
NEU_LABEL = "neutral"

SMOOTHING_ALPHA = 0.5
NEUTRAL_WEIGHT = 0.6
NEGATIVE_BIAS = 1.8
NEGATIVE_KEYWORD_HINTS = ['유출', '해킹', '피해', '제재', '과징금', '혼란', '벌금', '영업정지', '징벌', '유도', '위반', '사고', '사태', '철회']
POSITIVE_KEYWORD_HINTS = ['호재', '개선', '혁신', '활성화', '확대', '기대', '증가', '수주', '신기록', '성장', '달성', '선정']
KEYWORD_ADJUST = 0.04

VALID_POS = {"Noun", "Adjective", "Verb"}


class SentimentAnalyzer:
    """finance_sentiment_corpus 포맷의 감성 사전을 로드해 감정 점수를 계산한다."""

    def __init__(
        self,
        dataset_path: str = "finance_data.csv",
        *,
        csv_encoding: str = "utf-8",
        stemming: bool = True,
    ) -> None:
        script_dir = Path(__file__).resolve().parent
        candidate = Path(dataset_path)
        if not candidate.exists():
            candidate = script_dir / dataset_path
        if not candidate.exists():
            raise FileNotFoundError(
                f"감성 사전 CSV를 찾을 수 없습니다: '{dataset_path}'.\n"
                "finance_sentiment_corpus 저장소에서 finance_data.csv를 내려받아 동일 위치에 두세요."
            )

        self.dataset_path = candidate
        self.csv_encoding = csv_encoding
        self.okt = Okt()
        self.stemming = stemming

        self.dataset = self._load_dataset()
        self.word_scores = self._build_word_scores()

    # ------------------------------------------------------------------
    # 데이터 적재 및 전처리
    # ------------------------------------------------------------------
    def _load_dataset(self) -> pd.DataFrame:
        df = pd.read_csv(self.dataset_path, encoding=self.csv_encoding)
        df = df.rename(columns={c: c.strip().lower() for c in df.columns})

        if "labels" not in df.columns:
            raise ValueError("CSV에는 'labels' 컬럼이 필요합니다.")

        text_col_candidates = ["kor_sentence", "sentence", "text"]
        text_col = next((c for c in text_col_candidates if c in df.columns), None)
        if text_col is None:
            raise ValueError(
                "CSV에서 문장을 담고 있는 컬럼을 찾지 못했습니다.(kor_sentence, sentence 등)"
            )

        cleaned = df[["labels", text_col]].copy()
        cleaned[text_col] = cleaned[text_col].astype(str).str.strip()
        cleaned = cleaned[cleaned[text_col].str.len() > 0]
        cleaned["labels"] = cleaned["labels"].astype(str).str.lower().str.strip()
        cleaned = cleaned[cleaned["labels"].isin({POS_LABEL, NEG_LABEL, NEU_LABEL})]
        cleaned = cleaned.drop_duplicates(subset=[text_col, "labels"]).reset_index(drop=True)
        cleaned = cleaned.rename(columns={text_col: "text"})
        return cleaned

    # ------------------------------------------------------------------
    # 감성 사전 생성
    # ------------------------------------------------------------------
    def _tokenize(self, text: str) -> List[str]:
        tokens: List[str] = []
        for word, pos in self.okt.pos(text, norm=True, stem=self.stemming):
            if pos in VALID_POS and len(word) > 1:
                tokens.append(word)
        return tokens

    def _build_word_scores(self) -> dict[str, float]:
        label_counter: defaultdict[str, Counter[str]] = defaultdict(Counter)

        for label, text in self.dataset[["labels", "text"]].itertuples(index=False):
            tokens = set(self._tokenize(text))
            if not tokens:
                continue
            for token in tokens:
                label_counter[token][label] += 1

        scores: dict[str, float] = {}
        for token, counter in label_counter.items():
            pos = counter.get(POS_LABEL, 0)
            neg = counter.get(NEG_LABEL, 0)
            neu = counter.get(NEU_LABEL, 0)
            total = pos + neg + neu
            if total == 0:
                continue

            pos_smoothed = pos + SMOOTHING_ALPHA
            neg_smoothed = neg + SMOOTHING_ALPHA
            neu_smoothed = neu + SMOOTHING_ALPHA

            denom = pos_smoothed + neg_smoothed + neu_smoothed
            if denom == 0:
                continue

            if neg_smoothed > pos_smoothed:
                diff = (neg_smoothed - pos_smoothed) / denom
                score = -NEGATIVE_BIAS * diff
            else:
                score = (pos_smoothed - neg_smoothed) / denom

            neutral_ratio = neu_smoothed / denom
            score *= (1.0 - NEUTRAL_WEIGHT * neutral_ratio)
            scores[token] = score
        return scores

    # ------------------------------------------------------------------
    # 문장 분석 API
    # ------------------------------------------------------------------
    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        if not isinstance(text, str) or not text.strip():
            return NEU_LABEL, 0.0

        tokens = self._tokenize(text)
        if not tokens:
            return NEU_LABEL, 0.0

        scores: List[float] = [self.word_scores.get(token, 0.0) for token in tokens]
        non_zero = [s for s in scores if abs(s) > 1e-6]
        if not non_zero:
            return NEU_LABEL, 0.0

        avg_score = sum(non_zero) / len(non_zero)

        lowered_text = text.lower()
        if lower_word_hits := sum(kw in lowered_text for kw in NEGATIVE_KEYWORD_HINTS):
            avg_score -= KEYWORD_ADJUST * lower_word_hits
        if lower_word_hits_pos := sum(kw in lowered_text for kw in POSITIVE_KEYWORD_HINTS):
            avg_score += KEYWORD_ADJUST * lower_word_hits_pos

        if avg_score > 0.03:
            label = POS_LABEL
        elif avg_score < -0.015:
            label = NEG_LABEL
        else:
            label = NEU_LABEL
        return label, avg_score

    # ------------------------------------------------------------------
    # 유틸리티 함수
    # ------------------------------------------------------------------
    def analyze_sentences(self, texts: Iterable[str]) -> List[Tuple[str, float]]:
        return [self.analyze_sentiment(text) for text in texts]

    def debug_top_words(self, n: int = 30) -> List[Tuple[str, float]]:
        return sorted(
            self.word_scores.items(), key=lambda item: abs(item[1]), reverse=True
        )[:n]


if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    samples = [
        "매출이 증가하고 흑자로 전환했다.",
        "적자 확대와 비용 증가로 우려가 커진다.",
        "방향성 없이 혼조세가 이어진다.",
    ]

    for sentence in samples:
        sentiment, score = analyzer.analyze_sentiment(sentence)
        print(f"문장: {sentence}")
        print(f" -> 감정: {sentiment}, 점수: {score:.3f}\n")
