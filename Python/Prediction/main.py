"""
네이버 뉴스에서 기사 데이터를 수집하고 감성/키워드 분석 리포트를 생성하는 스크립트.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
import re

import dotenv
import requests
from bs4 import BeautifulSoup

from sentiment_analyzer import SentimentAnalyzer
from keyword_extractor import KeywordExtractor

FAIL_MESSAGE = "본문을 찾을 수 없습니다. (검수 필요)"
DEFAULT_SEARCH_WORD = "롯데"
MAX_ARTICLES_DEFAULT = 30
WINDOW_DAYS_DEFAULT = 7
SENTIMENT_POS_THRESHOLD = 0.02
SENTIMENT_NEG_THRESHOLD = -0.02


def filter_keywords(keywords: Iterable[str], *, min_core_length: int = 2) -> list[str]:
    cleaned: list[str] = []
    for kw in keywords:
        if not kw:
            continue
        kw_str = str(kw).strip()
        if not kw_str:
            continue
        if re.fullmatch(r'[\"\'`~!@#$%^&*()_+=\-\[\]{}|\\:;,.<>/?]+', kw_str):
            continue
        core = re.sub(r"[^0-9A-Za-z가-힣]", "", kw_str)
        if len(core) < min_core_length:
            continue
        cleaned.append(kw_str)
    return cleaned


def safe_print(text: str) -> None:
    """인코딩 오류 없이 문자열을 출력한다."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, "replace").decode(encoding))


def get_news_content(link: str, search_word: str = "") -> str:
    """뉴스 원문 페이지에서 본문 텍스트를 추출한다."""
    selectors = [
        "#article-view-content-div",
        "#articleBody",
        ".article_body",
        "#articleBodyContents",
        "#dic_area",
        ".article-veiw-body",
        "#article_txt",
        ".article-formatted-body",
        ".view_left",
        "#article_body",
        '[itemprop="articleBody"]',
        ".article_view",
    ]

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36"
            )
        }
        response = requests.get(link, headers=headers, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return FAIL_MESSAGE

    soup = BeautifulSoup(response.content, "html.parser")
    content = None
    for selector in selectors:
        content = soup.select_one(selector)
        if content:
            break

    if not content:
        return FAIL_MESSAGE

    for tag in content.find_all(["script", "style", "figure", "figcaption"]):
        tag.decompose()

    lines = content.get_text(separator="\n", strip=True).split("\n")
    unique_lines: list[str] = []
    seen = set()
    for line in lines:
        if line and line not in seen:
            unique_lines.append(line)
            seen.add(line)

    base_filter_keywords = [
        "기자", "무단전재", "재배포 금지", "Copyright", "특파원",
        "바로가기", "구독", "이메일", "URL", "보내기", "사진",
    ]
    dynamic_filter = [kw for kw in base_filter_keywords if kw.lower() != search_word.lower()]
    email_filters = ["@", ".co.kr", ".com", ".net", ".kr"]

    clean_lines: list[str] = []
    for line in unique_lines:
        if any(keyword in line for keyword in dynamic_filter):
            continue
        if any(token in line for token in email_filters):
            continue
        clean_lines.append(line)

    text_content = "\n".join(clean_lines).strip()
    return text_content if len(text_content) > 100 else FAIL_MESSAGE


def fetch_recent_news(
    search_word: str,
    *,
    client_id: str,
    client_secret: str,
    max_articles: int = MAX_ARTICLES_DEFAULT,
    window_days: int = WINDOW_DAYS_DEFAULT,
) -> list[dict[str, str]]:
    """네이버 뉴스 API로 최신 기사 목록을 가져온다."""
    enc_text = urllib.parse.quote(search_word)
    earliest_allowed = datetime.now(timezone.utc) - timedelta(days=window_days)

    successful_articles: list[dict[str, str]] = []
    seen_links: set[str] = set()
    start_index = 1
    display_count = 100
    found_old_article = False

    safe_print(
        f"'{search_word}' 검색 결과를 수집합니다 ({window_days}일 이내, 최대 {max_articles}건)"
    )

    while (
        len(successful_articles) < max_articles
        and not found_old_article
        and start_index <= 1000
    ):
        url = (
            "https://openapi.naver.com/v1/search/news.json?"
            f"query={enc_text}&display={display_count}&start={start_index}&sort=date"
        )

        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)

        try:
            with urllib.request.urlopen(request) as response:
                if response.getcode() != 200:
                    print(f"API Error Code: {response.getcode()}")
                    break
                response_body = response.read()
            news_data = json.loads(response_body.decode("utf-8"))
        except Exception as exc:
            print(f"요청 중 오류 발생: {exc}")
            break

        items = news_data.get("items", [])
        if not items:
            print("더 이상 검색 결과가 없습니다.")
            break

        for item in items:
            pub_date_str = item.get("pubDate")
            if not pub_date_str:
                continue
            try:
                article_date = datetime.strptime(
                    pub_date_str, "%a, %d %b %Y %H:%M:%S %z"
                )
            except ValueError:
                continue

            if article_date < earliest_allowed:
                found_old_article = True
                print("--- 지정 기간 이전 기사 발견. 수집을 종료합니다. ---")
                break

            original_link = item.get("originallink") or item.get("link")
            if not original_link or original_link in seen_links:
                continue
            seen_links.add(original_link)

            title = item.get("title")
            if not title:
                continue

            clean_title = BeautifulSoup(title, "html.parser").get_text()
            if 'newsis.com' in original_link:
                safe_print(
                    f"- 제외 (본문 제한 가능성): {clean_title.replace('\n', ' ')[:40]}..."
                )
                continue

            content = get_news_content(original_link, search_word)
            if content == FAIL_MESSAGE:
                continue

            formatted_date = article_date.strftime("%Y-%m-%d")
            successful_articles.append(
                {
                    "title": clean_title,
                    "link": original_link,
                    "date": formatted_date,
                    "content": content,
                }
            )
            safe_print(
                f"- 수집 진행: {len(successful_articles)}/{max_articles}건 확보 - "
                f"'{clean_title[:40]}...'"
            )

            if len(successful_articles) >= max_articles:
                break

        start_index += display_count

    print("\n" + "=" * 50)
    print(f"총 {len(successful_articles)}건의 기사 수집 완료")
    print("=" * 50 + "\n")
    return successful_articles


def generate_comprehensive_report(
    stock_name: str,
    news_list: list[dict[str, str]],
    resources_dir: str,
) -> dict:
    """감성/키워드 분석 결과를 포함한 리포트를 생성한다."""
    print(f"[Start] Analysis for '{stock_name}'")

    print("1) Sentiment analysis..")
    senti_path = os.path.join(resources_dir, "finance_data.csv")
    sentiment_analyzer = SentimentAnalyzer(dataset_path=senti_path)
    keyword_extractor = KeywordExtractor()

    total_sentiment_score = 0.0
    sentiment_counts = Counter()
    news_contents = []

    for news in news_list:
        content = str(news.get("content", ""))
        news_contents.append(content)
        sentiment_class, score = sentiment_analyzer.analyze_sentiment(content)
        total_sentiment_score += score

        normalized_label = sentiment_class.strip().lower()
        label_map = {
            'positive': 'positive',
            'negative': 'negative',
            'neutral': 'neutral',
            '긍정': 'positive',
            '부정': 'negative',
            '중립': 'neutral',
        }
        normalized_label = label_map.get(normalized_label, 'neutral')

        if normalized_label == 'positive':
            sentiment_counts['positive'] += 1
        elif normalized_label == 'negative':
            sentiment_counts['negative'] += 1
        else:
            sentiment_counts['neutral'] += 1

        news['sentimentClass'] = normalized_label
        article_keywords = keyword_extractor.extract_keywords(content, num_keywords=5)
        news["topKeywords"] = filter_keywords(article_keywords)

    avg_sentiment_score = total_sentiment_score / len(news_list) if news_list else 0.0

    print("2) Keyword extraction..")
    full_news_text = " ".join(news_contents)
    detailed_keywords = keyword_extractor.extract_keywords(
        full_news_text, num_keywords=50, return_detail=True
    )

    filtered_keywords = []
    for item in detailed_keywords:
        keyword = item["keyword"].strip()
        if stock_name in keyword or keyword in stock_name:
            continue
        cleaned = filter_keywords([keyword])
        if not cleaned:
            continue
        filtered_item = dict(item)
        filtered_item["keyword"] = cleaned[0]
        filtered_keywords.append(filtered_item)

    word_cloud_data = {
        item["keyword"]: item.get("frequency", 1) for item in filtered_keywords
    }

    print("3) Building report..")
    report = {
        "stockName": stock_name,
        "analysisDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sentimentAnalysis": {
            "averageScore": round(avg_sentiment_score, 4),
            "overallSentiment": (
                "positive"
                if avg_sentiment_score > SENTIMENT_POS_THRESHOLD
                else (
                    "negative"
                    if avg_sentiment_score < SENTIMENT_NEG_THRESHOLD
                    else "neutral"
                )
            ),
            "sentimentDistribution": dict(sentiment_counts),
        },
        "keywordAnalysis": {"wordCloud": word_cloud_data},
        "relatedNews": news_list,
    }

    print(f"[Done] Analysis for '{stock_name}' complete.")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="네이버 뉴스 수집 및 감성 리포트 생성"
    )
    parser.add_argument(
        "--search-word",
        default=DEFAULT_SEARCH_WORD,
        help="네이버 뉴스 검색어 (기본: 삼성전자)",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=MAX_ARTICLES_DEFAULT,
        help="수집할 기사 수 (기본: 30)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=WINDOW_DAYS_DEFAULT,
        help="조회 기간(일) (기본: 7)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="리포트를 저장할 JSON 경로 (기본: data/final_report.json)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    data_dir = repo_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    dotenv_path = repo_root / ".env"
    if dotenv_path.exists():
        dotenv.load_dotenv(dotenv_path=dotenv_path)

    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 환경 변수가 설정되지 않았습니다.")
        print(".env 파일을 확인해 주세요.")
        return

    news_data = fetch_recent_news(
        args.search_word,
        client_id=client_id,
        client_secret=client_secret,
        max_articles=args.max_articles,
        window_days=args.window_days,
    )
    if not news_data:
        print("수집된 뉴스가 없어서 리포트를 생성할 수 없습니다.")
        return

    report = generate_comprehensive_report(
        args.search_word,
        news_data,
        resources_dir=str(script_dir),
    )

    output_path = args.output or (data_dir / "final_report.json")
    try:
        with output_path.open("w", encoding="utf-8") as fp:
            json.dump(report, fp, ensure_ascii=False, indent=4)
        print(f"\n리포트를 '{output_path}'에 저장했습니다.")
    except Exception as exc:
        print(f"리포트 저장 중 오류가 발생했습니다: {exc}")


if __name__ == "__main__":
    main()
