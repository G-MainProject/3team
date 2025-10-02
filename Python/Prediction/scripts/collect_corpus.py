"""
네이버 뉴스에서 최신 기사를 수집해 감성 사전 구축용 CSV를 생성하는 스크립트.
"""
import argparse
import csv
from datetime import datetime
from pathlib import Path
import sys

POSITIVE_KEYWORDS = [
    "증가", "개선", "호조", "확대", "수주", "달성", "상승", "호재", "신기록", "투자", "흑자",
]
NEGATIVE_KEYWORDS = [
    "감소", "악화", "우려", "적자", "축소", "부진", "하락", "리스크", "소송", "중단", "손실",
]
STRONG_POSITIVE_PHRASES = [
    "사상 최고", "최대 실적", "흑자 전환", "대규모 투자", "호평", "긍정적",
]
STRONG_NEGATIVE_PHRASES = [
    "최대 손실", "적자 전환", "대규모 감원", "리콜", "경영난", "비리",
]

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR.parent / ".." / "data"
DATA_DIR = DATA_DIR.resolve()

sys.path.insert(0, str(PROJECT_DIR))

def infer_sentiment_label(text: str) -> str:
    """간단한 키워드 기반 휴리스틱으로 감정 라벨을 추정합니다."""
    if not text:
        return "neutral"

    score = 0

    for phrase in STRONG_POSITIVE_PHRASES:
        if phrase in text:
            score += 2
    for phrase in STRONG_NEGATIVE_PHRASES:
        if phrase in text:
            score -= 2

    for keyword in POSITIVE_KEYWORDS:
        if keyword in text:
            score += 1
    for keyword in NEGATIVE_KEYWORDS:
        if keyword in text:
            score -= 1

    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"

from main import fetch_recent_news_from_naver, safe_print, DEFAULT_SEARCH_WORD  # noqa: E402


def collect_articles(search_word: str, max_articles: int, window_days: int) -> list[dict[str, str]]:
    articles = fetch_recent_news_from_naver(
        search_word,
        max_articles=max_articles,
        window_days=window_days,
    )
    if not articles:
        safe_print("기사 수집 결과가 없습니다. 검색어/인증 정보를 확인하세요.")
    return articles


def save_corpus_csv(articles: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["labels", "kor_sentence", "title", "date", "link"])
        for item in articles:
            content = (item.get("content") or "").replace("\n", " ").strip()
            title = (item.get("title") or "").replace("\n", " ").strip()
            if not content:
                continue
            label = infer_sentiment_label(content + " " + title)
            writer.writerow([
                label,
                content,
                title,
                item.get("date", ""),
                item.get("link", ""),
            ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="네이버 뉴스 기사 수집 후 감성 사전 구축용 CSV 파일 생성"
    )
    parser.add_argument(
        "--search-word",
        default=DEFAULT_SEARCH_WORD,
        help="네이버 뉴스 검색어 (기본: DEFAULT_SEARCH_WORD 환경 변수 또는 설정된 기본값)",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=200,
        help="수집할 기사 수 (기본: 200)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="수집 기간(일) (기본: 7)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="결과 CSV 경로 (기본: data/raw_corpus_<날짜>.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    articles = collect_articles(
        search_word=args.search_word,
        max_articles=args.max_articles,
        window_days=args.window_days,
    )
    if not articles:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = args.output or (DATA_DIR / f"raw_corpus_{timestamp}.csv")

    save_corpus_csv(articles, output_path)
    safe_print(f"기사 {len(articles)}건을 '{output_path}'에 저장했습니다.\n")
    safe_print("Labels are auto-inferred; please review and correct if needed.")


if __name__ == "__main__":
    main()



