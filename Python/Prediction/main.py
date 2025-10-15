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
DEFAULT_SEARCH_WORD_FALLBACK = "한화"
MAX_ARTICLES_DEFAULT = 30
WINDOW_DAYS_DEFAULT = 7
SENTIMENT_POS_THRESHOLD = 0.03
SENTIMENT_NEG_THRESHOLD = -0.03


# top_movers_auto.json에서 추출한 기본 검색어 목록을 읽어온다.
def _load_default_search_targets() -> tuple[list[str], dict[str, str], str | None]:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    candidate_paths = [
        repo_root / "data" / "raws" / "top_movers_auto.json",
    ]

    payload: dict | None = None
    for data_path in candidate_paths:
        if not data_path.exists():
            continue
        try:
            with data_path.open("r", encoding="utf-8") as fp:
                payload = json.load(fp)
            break
        except FileNotFoundError:
            continue
        except (json.JSONDecodeError, OSError):
            return [], {}, None

    if payload is None:
        return [], {}, None

    market_value = payload.get("market")
    market = market_value.strip() if isinstance(market_value, str) else None

    names: list[str] = []
    name_to_stock_code: dict[str, str] = {}
    seen: set[str] = set()

    details = payload.get("details")
    if isinstance(details, list):
        for entry in details:
            if not isinstance(entry, dict):
                continue
            raw_name = entry.get("name")
            if not isinstance(raw_name, str):
                continue
            candidate = raw_name.strip()
            if not candidate:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            names.append(candidate)

            raw_stock_code = entry.get("ticker")
            if isinstance(raw_stock_code, str):
                stock_code_candidate = raw_stock_code.strip()
                if stock_code_candidate:
                    name_to_stock_code[candidate] = stock_code_candidate
    return names, name_to_stock_code, market


DEFAULT_SEARCH_WORDS, DEFAULT_STOCK_CODE_MAP, DEFAULT_MARKET = _load_default_search_targets()
if not DEFAULT_SEARCH_WORDS:
    DEFAULT_SEARCH_WORDS = [DEFAULT_SEARCH_WORD_FALLBACK]
    DEFAULT_STOCK_CODE_MAP = {}
    DEFAULT_MARKET = None
DEFAULT_SEARCH_WORD = DEFAULT_SEARCH_WORDS[0]


# 추출된 키워드를 정규화하고 노이즈를 제거한다.
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


# 콘솔 인코딩 문제 없이 안전하게 문자열을 출력한다.
def safe_print(text: str) -> None:
    """인코딩 오류 없이 문자열을 출력한다."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(text.encode(encoding, "replace").decode(encoding))


# 뉴스 링크에서 본문을 가져와 정제한다.
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

    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        apparent = response.apparent_encoding
        if apparent:
            response.encoding = apparent
    html_text = response.text

    soup = BeautifulSoup(html_text, "html.parser")
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


# 네이버 뉴스 검색 API를 호출해 최신 기사를 모은다.
def fetch_recent_news(
    search_word: str,
    *,
    client_id: str,
    client_secret: str,
    max_articles: int | None = MAX_ARTICLES_DEFAULT,
    window_days: int = WINDOW_DAYS_DEFAULT,
) -> list[dict[str, str]]:
    """네이버 뉴스 API로 최신 기사 목록을 가져온다."""
    enc_text = urllib.parse.quote(search_word)
    earliest_allowed = datetime.now(timezone.utc) - timedelta(days=window_days)

    successful_articles: list[dict[str, str]] = []
    seen_links: set[str] = set()
    start_index = 1
    display_count = 100
    old_article_notice_printed = False

    limit_text = (
        f"최대 {max_articles}건" if max_articles is not None else "최대 건수 제한 없음"
    )
    safe_print(
        f"'{search_word}' 검색 결과를 수집합니다 ({window_days}일 이내, {limit_text})"
    )

    while (
        (max_articles is None or len(successful_articles) < max_articles)
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

            threshold_local_date = earliest_allowed.astimezone(article_date.tzinfo).date()
            if article_date.date() < threshold_local_date:
                if not old_article_notice_printed:
                    print("--- 지정 기간 이전 기사 발견. 이후 기사는 건너뜁니다. ---")
                    old_article_notice_printed = True
                continue

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
            progress_text = (
                f"{len(successful_articles)}/{max_articles}"
                if max_articles is not None
                else f"{len(successful_articles)}"
            )
            safe_print(
                f"- 수집 진행: {progress_text}건 확보 - '{clean_title[:40]}...'"
            )

            if max_articles is not None and len(successful_articles) >= max_articles:
                break

        start_index += display_count

    print("\n" + "=" * 50)
    print(f"총 {len(successful_articles)}건의 기사 수집 완료")
    print("=" * 50 + "\n")
    return successful_articles


# 주식 분석 결과를 감성·키워드·뉴스 보고서로 구성한다.
def generate_comprehensive_report(
    stock_name: str,
    news_list: list[dict[str, str]],
    resources_dir: str,
    stock_code: str | None = None,
    market: str | None = None,
) -> dict:
    """감성/키워드 분석 결과를 포함한 리포트를 생성한다."""
    print(f"[Start] Analysis for '{stock_name}'")
    market = market or DEFAULT_MARKET

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
        **({"market": market} if market else {}),
        "stockCode": stock_code,
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


# 분석에 사용할 명령줄 인자를 설정한다.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="네이버 뉴스 수집 및 감성 리포트 생성"
    )
    parser.add_argument(
        "--search-word",
        default=None,
        help=f"네이버 뉴스 검색어 (미입력 시 top_movers_auto.json 이름 순회, 기본 첫 종목: {DEFAULT_SEARCH_WORD})",
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


# 뉴스 수집부터 보고서 저장까지 전체 흐름을 실행한다.
def main() -> None:
    args = parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    data_dir = repo_root / "data/raws"
    data_dir.mkdir(parents=True, exist_ok=True)

    dotenv_path = repo_root / ".env"
    if dotenv_path.exists():
        dotenv.load_dotenv(dotenv_path=dotenv_path)

    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 환경 변수가 설정되어 있지 않습니다.")
        print(".env 파일을 확인해주세요.")
        return

    if args.search_word:
        search_words = [args.search_word.strip()]
    else:
        search_words = [word.strip() for word in DEFAULT_SEARCH_WORDS]

    search_words = [word for word in search_words if word]
    if not search_words:
        search_words = [DEFAULT_SEARCH_WORD_FALLBACK]

    base_output = args.output or (data_dir / "sentiment_report.json")

    aggregated_reports: list[dict] = []
    failed_targets: list[str] = []

    for idx, search_word in enumerate(search_words, start=1):
        print(f"\n=== [{idx}/{len(search_words)}] '{search_word}' 분석 시작 ===")
        news_data = fetch_recent_news(
            search_word,
            client_id=client_id,
            client_secret=client_secret,
            max_articles=args.max_articles,
            window_days=args.window_days,
        )
        if not news_data:
            print("뉴스를 충분히 가져오지 못해 보고서를 생성하지 않습니다.")
            failed_targets.append(search_word)
            continue

        stock_code = DEFAULT_STOCK_CODE_MAP.get(search_word)
        report = generate_comprehensive_report(
            search_word,
            news_data,
            resources_dir=str(script_dir),
            stock_code=stock_code,
            market=DEFAULT_MARKET,
        )

        aggregated_reports.append(report)
        print("\n보고서를 메모리에 누적했습니다.")

    if aggregated_reports:
        try:
            final_payload = (
                aggregated_reports
                if len(aggregated_reports) > 1
                else aggregated_reports[0]
            )
            with base_output.open("w", encoding="utf-8") as fp:
                json.dump(final_payload, fp, ensure_ascii=False, indent=4)
            print(f"\n보고서를 '{base_output}'에 저장했습니다.")
        except Exception as exc:
            print(f"보고서 저장 중 오류가 발생했습니다: {exc}")

    if failed_targets:
        print("\n[기본 분석] 실패한 검색어:")
        for word in failed_targets:
            print(f" - {word}")

if __name__ == "__main__":
    main()
