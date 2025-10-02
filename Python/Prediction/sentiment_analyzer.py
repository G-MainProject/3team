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

# 감정 레이블과 모델 하이퍼파라미터를 정의
POS_LABEL = "positive"
NEG_LABEL = "negative"
NEU_LABEL = "neutral"

SMOOTHING_ALPHA = 1.0
MIN_TOKEN_FREQ = 2
NEUTRAL_LOG_PENALTY = 1.0

POSITIVE_CHUNK_KEYWORDS = {
    '상승': 0.4,
    '급등': 0.6,
    '상한가': 0.8,
    '강세': 0.35,
    '호재': 0.45,
    '확대': 0.3,
    '확보': 0.3,
    '성공': 0.4,
    '개선': 0.35,
    '수주': 0.4,
    '호황': 0.35,
    '호조': 0.35,
}
NEGATIVE_CHUNK_KEYWORDS = {
    '악화': 0.6,
    '하락': 0.45,
    '급락': 0.55,
    '우려': 0.4,
    '불안': 0.35,
    '리콜': 0.55,
    '불만': 0.45,
    '관망세': 0.3,
    '약세': 0.4,
    '중단': 0.45,
    '손실': 0.5,
    '실패': 0.5,
    '적자': 0.5,
    '긴급': 0.3,
    '위기': 0.45,
}
CHUNK_POS_THRESHOLD = 0.25
CHUNK_NEG_THRESHOLD = -0.25





VALID_POS = {"Noun", "Adjective", "Verb"}


    # 데이터를 불러와 학습하고 문장을 채점하는 핵심 분석기
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
        self.vocab: set[str] = set()
        self.class_priors: dict[str, float] = {}
        self.token_log_probs: dict[str, dict[str, float]] = {}
        self.default_log_prob: dict[str, float] = {}
        self._build_model()

    # ------------------------------------------------------------------
    # 데이터 적재 및 전처리
    # ------------------------------------------------------------------
        # 금융 감성 데이터셋을 읽어 정제
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
        # 텍스트를 정규화하고 유용한 토큰만 추출
    def _tokenize(self, text: str) -> List[str]:
        tokens: List[str] = []
        for word, pos in self.okt.pos(text, norm=True, stem=self.stemming):
            if pos in VALID_POS and len(word) > 1:
                tokens.append(word)
        return tokens

    def _chunk_sentence(self, text: str) -> list[str]:
        """문장을 간단한 품사 규칙으로 묶은 청크 리스트로 변환"""
        tagged = self.okt.pos(text, norm=True, stem=self.stemming)
        chunks: list[str] = []
        current: list[str] = []
        for word, pos in tagged:
            if pos in {"Noun", "Adjective", "Verb", "Adverb"}:
                current.append(word)
            else:
                if current:
                    chunks.append(' '.join(current))
                    current = []
        if current:
            chunks.append(' '.join(current))
        return chunks

        # 라벨별 토큰 빈도로 다항 나이브 베이즈 모델을 학습
    def _build_model(self) -> None:
        token_counts: dict[str, Counter[str]] = {POS_LABEL: Counter(), NEG_LABEL: Counter(), NEU_LABEL: Counter()}
        doc_counts: Counter[str] = Counter()
        total_tokens_per_label: dict[str, int] = {POS_LABEL: 0, NEG_LABEL: 0, NEU_LABEL: 0}

        for label, text in self.dataset[["labels", "text"]].itertuples(index=False):
            tokens = self._tokenize(text)
            if not tokens:
                continue
            doc_counts[label] += 1
            for token in tokens:
                token_counts[label][token] += 1
                total_tokens_per_label[label] += 1
                self.vocab.add(token)

        total_docs = sum(doc_counts.values()) or 1
        num_classes = 3
        vocab_size = len(self.vocab) or 1

        self.class_priors = {
            label: math.log((doc_counts.get(label, 0) + 1) / (total_docs + num_classes))
            for label in (POS_LABEL, NEG_LABEL, NEU_LABEL)
        }

        self.token_log_probs = {label: {} for label in (POS_LABEL, NEG_LABEL, NEU_LABEL)}
        self.default_log_prob = {}
        for label in (POS_LABEL, NEG_LABEL, NEU_LABEL):
            denominator = total_tokens_per_label[label] + SMOOTHING_ALPHA * vocab_size
            self.default_log_prob[label] = math.log(SMOOTHING_ALPHA / denominator)
            for token in self.vocab:
                count = token_counts[label][token]
                prob = (count + SMOOTHING_ALPHA) / denominator
                self.token_log_probs[label][token] = math.log(prob)

        # 지나치게 드문 토큰은 어휘에서 제거 (가벼운 스무딩)
        rare_tokens = {token for token in self.vocab if sum(token_counts[label][token] for label in token_counts) < MIN_TOKEN_FREQ}
        if rare_tokens:
            for token in rare_tokens:
                for label in self.token_log_probs:
                    self.token_log_probs[label].pop(token, None)
            self.vocab -= rare_tokens
    # ------------------------------------------------------------------
    # 문장 분석 API
    # ------------------------------------------------------------------
        # 한 문장의 감정을 추론해 라벨과 점수 반환
    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
                # 감성 계산 핵심 구간 (청크 기반)
        # 품사 태깅으로 만든 청크에서 긍/부정 핵심어를 찾아 가중치를 합산하고
        # 최종 점수에 따라 positive/negative/neutral 레이블을 선택
        if not isinstance(text, str) or not text.strip():
            return NEU_LABEL, 0.0

        chunks = self._chunk_sentence(text)
        if not chunks:
            return NEU_LABEL, 0.0

        chunk_score = 0.0
        positive_hits = 0
        negative_hits = 0

        for chunk in chunks:
            lower_chunk = chunk.lower()
            for keyword, weight in POSITIVE_CHUNK_KEYWORDS.items():
                if keyword in lower_chunk:
                    chunk_score += weight
                    positive_hits += 1
            for keyword, weight in NEGATIVE_CHUNK_KEYWORDS.items():
                if keyword in lower_chunk:
                    chunk_score -= weight
                    negative_hits += 1

        if positive_hits == 0 and negative_hits == 0:
            return NEU_LABEL, 0.0

        chunk_score += 0.05 * (positive_hits - negative_hits)
        chunk_score = max(-1.0, min(1.0, chunk_score))

        if chunk_score >= CHUNK_POS_THRESHOLD:
            return POS_LABEL, chunk_score
        if chunk_score <= CHUNK_NEG_THRESHOLD:
            return NEG_LABEL, chunk_score
        return NEU_LABEL, chunk_score


    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # 유틸리티 함수
    # ------------------------------------------------------------------
        # 여러 문장을 한 번에 채점하는 래퍼
    def analyze_sentences(self, texts: Iterable[str]) -> List[Tuple[str, float]]:
        return [self.analyze_sentiment(text) for text in texts]

        # 분류에 크게 기여하는 토큰을 확인
    def debug_top_words(self, n: int = 30) -> List[Tuple[str, float]]:
        ranking: List[Tuple[str, float]] = []
        for token in self.vocab:
            pos_log = self.token_log_probs[POS_LABEL].get(token, self.default_log_prob[POS_LABEL])
            neg_log = self.token_log_probs[NEG_LABEL].get(token, self.default_log_prob[NEG_LABEL])
            ranking.append((token, pos_log - neg_log))
        return sorted(ranking, key=lambda item: abs(item[1]), reverse=True)[:n]


if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    samples = [
        "이외에도 텔코웨어가 9.55% 상승하며 15,940원에 거래 중이고, 천연가스 가격 하락에 따라 인버스 천연가스 관련 ETN 종목들이 8%대 강세를 보이고 있다.",
        "한편 독립 리서치 기관 그로쓰리서치는 이날 발간한 보고서에서 MASH 치료제 시장이 2032년까지 연평균 38.2%의 폭발적인 성장을 기록할 것으로 전망했다.",
        "특히 9월 중순부터 연속 상한가 랠리를 이어온 코오롱모빌리티그룹은 지난 19일 단기 급락세를 경험했으나, 불과 한 거래일 만에 다시 상한가로 복귀하며 강한 매수세를 입증했다.",
        "11일 이후 5거래일 연속 상한가에 도달한 뒤 19일에는 26%대 급락 마감했다.",
        "반면 약세 업종에 대한 언급은 제한적이며, 현재 시점에서는 상승 업종의 폭이 상대적으로 넓게 관찰된다.",
        "코스피 시가총액 상위 종목들 중 △삼성전자(+3.39%) △LG에너지솔루션(+0.86%) △KB금융(+0.69%) △HD현대중공업(+1.32%) △현대차(+0.93%) △두산에너빌리티(+4.61%) △신한지주(+0.86%) 등은 상승 중이고, △삼성바이오로직스(-0.39%) △한화에어로스페이스(-0.59%) △셀트리온(-0.76%) △네이버(-0.21%) △한화오션(-1.61%) 등의 주가는 하락세를 탔다.",
        "[알림] 본 기사는 투자판단의 참고용이며, 이를 근거로 한 투자손실에 대한 책임은 없습니다.",
        "코오롱 완전 자회사 편입 소식에 급등세를 이어가며 투자경고 종목으로까지 지정됐던 코오롱모빌리티그룹 주가가 돌연 급락했다.",
        "완전 자회사 합병으로 내년 초 상장폐지를 추진하는 가운데 과열된 주가 흐름에 대해 우려의 시선이 나온다.",
        "관련업계는 이 같은 급락세를 예견했다는 분위기다.",
        "그러나 주가가 단기간 수배 치솟은 상황에서 상장 폐지가 진행될 경우 주주들의 불이익이 있을 수 있다는 우려도 나온다.",
        "실제 지난해 코오롱모빌리티그룹의 실적은 고금리에 따른 소비 위축과 전기차 수요 둔화 지속 등의 영향으로 당기순손실 64억원을 기록했다.",
        "업종별 흐름을 보면 전기장비 업종이 3.11% 오르며 두드러진 강세를 보이고 있다.",
        "이어 에너지장비및서비스가 2.07%, 광고가 1.90%, 비철금속이 1.64% 상승 중이다.",
        "담배 업종도 1.61% 오르며 선방하는 가운데 반도체와반도체장비가 1.59% 오르며 지수를 지지하고 있다.",
        "소프트웨어와 건강관리기술, 생명보험, 생명과학도구및서비스 역시 1%대 오름세를 나타내며 전반적으로 업종별 강세 흐름이 뚜렷하다.",
        "특히 반도체 업종은 삼성전자를 비롯한 대형주의 낙관적인 전망이 맞물리며 외국인 매수 기대감을 자극하고 있다.",
        "테마별로는 AI와 신성장 산업 관련주가 두각을 드러내고 있다.",
        "AI 챗봇 테마가 2.97% 오르며 폴라리스AI와 마음AI의 강세가 두드러지고 있다.",
        "퓨리오사AI 테마는 2.34% 상승하며 DSC인베스트먼트와 와이즈넛이 동반 강세를 기록 중이다.",
        "지능형 로봇·AI 관련 종목도 1.63% 오르며 한라캐스트와 마음AI가 상승 흐름을 주도하고 있다.",
        "2025년 하반기 신규 상장 테마 역시 1.59% 오르며 프로티나와 한라캐스트가 주목받고 있다.",
        "전선, IT 대표주, 의료AI, 미용기기, 딥페이크, 전력설비 테마 역시 일제히 상승세를 보이며 시장 내에서 신기술과 미래 산업에 대한 기대가 여전함을 보여준다.",
        "다만 코오롱모빌리티그룹우가 19.48% 급등하며 36,500원에 거래되고 있고, 코오롱모빌리티그룹 본주도 18.72% 오르며 14,970원에 거래되며 투자자들의 관심을 끌고 있다.",
        "우진과 한미약품 역시 8%대 상승률을 기록하며 코스피 내 강세주로 부각되고 있다.",
        "코스닥 시장에서는 비올이 27,150원에 거래되며 29.90%의 급등으로 상한가에 도달했다.",
        "또 다른 상한가 종목으로는 에코글로우가 789원에 거래되며 29.56% 상승률을 기록하고 있다.",
        "신규 상장주인 프로티나는 25.75% 급등하며 42,000원에 거래되고 있고, AI 테마주인 폴라리스AI와 마음AI 역시 각각 15.53%, 10.84%의 강세를 보이고 있다.",
        "이외에도 에이프릴바이오, 큐라클, 에스디시스템, 대한광통신, 한라캐스트 등이 9∼14%대 상승률을 기록하며 시장 내 매수세를 주도하고 있다.",
        "이재명 대통령이 과거 후보 시절 투자한 것으로 알려진 ETF KODEX 200은 48,355원에 거래되며 0.84% 상승하고 있다."
    ]









    for sentence in samples:
        sentiment, score = analyzer.analyze_sentiment(sentence)
        print(f"문장: {sentence}")
        print(f" -> 감정: {sentiment}, 점수: {score:.3f}\n")
