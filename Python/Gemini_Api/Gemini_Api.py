import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dotenv
import google.generativeai as genai


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent.parent / "data"
RAWS_DIR = DATA_DIR / "raws"
RAWS_DIR.mkdir(parents=True, exist_ok=True)

PERIOD_ORDER = ["하루", "일주일", "한 달", "6개월", "일 년"]
ALLOWED_VERDICTS = {"강력매수", "매수", "보유", "매도", "강력매도"}


dotenv.load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def normalize_key(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or "").strip())


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(
            f"오류: '{path.resolve()}' 경로에서 JSON 파일을 찾을 수 없습니다. "
            "파일 이름과 위치를 확인해 주세요."
        )
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"오류: '{path.name}' 파일을 JSON으로 해석하지 못했습니다. 상세: {exc}")
        sys.exit(1)


def summarize_sentiment_report(entries, target_name: str | None = None) -> str:
    lines = []
    target_norm = normalize_key(target_name)

    for entry in entries or []:
        stock_name = entry.get("stockName")
        if target_name and normalize_key(stock_name) != target_norm:
            continue

        name = stock_name or "N/A"
        code = entry.get("stockCode", "N/A")
        analysis = entry.get("sentimentAnalysis", {}) or {}
        average_score = analysis.get("averageScore")
        average_display = (
            f"{average_score:.4f}" if isinstance(average_score, (int, float)) else "N/A"
        )
        overall = analysis.get("overallSentiment", "N/A")
        distribution = analysis.get("sentimentDistribution", {}) or {}
        distribution_display = ", ".join(
            f"{key}:{value}" for key, value in distribution.items() if value is not None
        )

        keyword_dict = entry.get("keywordAnalysis", {}).get("wordCloud", {}) or {}
        keyword_items = [
            (word, count)
            for word, count in keyword_dict.items()
            if isinstance(count, (int, float))
        ]
        keyword_items.sort(key=lambda item: item[1], reverse=True)
        top_keywords = ", ".join(
            f"{word}:{count}" for word, count in keyword_items[:5]
        )

        parts = [
            f"종목:{name}",
            f"코드:{code}",
            f"평균점수:{average_display}",
            f"전체정서:{overall}",
        ]
        if distribution_display:
            parts.append(f"분포:{distribution_display}")
        if top_keywords:
            parts.append(f"상위키워드:{top_keywords}")
        lines.append("- " + " | ".join(parts))

        news_list = entry.get("relatedNews", []) or []
        for news in news_list[:2]:
            title = news.get("title")
            sentiment_class = news.get("sentimentClass", "N/A")
            if title:
                lines.append(f"  - 뉴스[{sentiment_class}]: {title}")

    return "\n".join(lines) if lines else "자료 없음"


def summarize_top_movers(report, target_name: str | None = None, target_ticker: str | None = None) -> str:
    details = report.get("details", []) if isinstance(report, dict) else []
    lines = []
    target_norm = normalize_key(target_name)
    target_ticker_norm = normalize_key(target_ticker)

    for item in details:
        name = item.get("name", "N/A")
        ticker = item.get("ticker", "N/A")
        if target_name and not (
            normalize_key(name) == target_norm
            or (target_ticker and normalize_key(ticker) == target_ticker_norm)
        ):
            continue

        change_pct = item.get("change_pct")
        price = item.get("current_price")
        change_display = (
            f"{change_pct:.2f}%" if isinstance(change_pct, (int, float)) else "N/A"
        )
        price_display = (
            f"{price:,.2f}" if isinstance(price, (int, float)) else "N/A"
        )
        lines.append(
            f"- 종목:{name}({ticker}) | 변동률:{change_display} | 현재가:{price_display}"
        )

    if not lines and not target_name:
        market_value = report.get("market")
        date_value = report.get("date")
        header_parts = []
        if date_value:
            header_parts.append(f"기준일:{date_value}")
        if market_value:
            header_parts.append(f"시장:{market_value}")
        if header_parts:
            lines.append("- " + " | ".join(header_parts))

    return "\n".join(lines) if lines else "자료 없음"


def find_chart_item(chart_payload, target_name: str | None, target_ticker: str | None):
    items = chart_payload.get("items") if isinstance(chart_payload, dict) else None
    if not items:
        return None

    target_norm = normalize_key(target_name)
    target_ticker_norm = normalize_key(target_ticker)

    for item in items:
        meta = item.get("meta", {}) or {}
        name_norm = normalize_key(meta.get("name"))
        ticker_norm = normalize_key(meta.get("ticker"))
        if target_name and name_norm == target_norm:
            return item
        if target_ticker and ticker_norm == target_ticker_norm:
            return item
    return None


def summarize_chart_item(item) -> str:
    if not item:
        return "자료 없음"

    period_map = {
        "하루": 1,
        "일주일": 7,
        "한 달": 30,
        "6개월": 180,
        "일 년": 365,
    }

    meta = item.get("meta", {}) or {}
    name = meta.get("name", "N/A")
    ticker = meta.get("ticker", "N/A")
    rows = item.get("rows", []) or []

    if not rows:
        return f"- 종목:{name}({ticker}) | 시세 데이터가 없습니다."

    rows_sorted = sorted(rows, key=lambda row: row.get("date", ""))
    latest = rows_sorted[-1]
    latest_date = latest.get("date", "N/A")
    latest_close = latest.get("close")
    latest_close_text = (
        f"{latest_close:,.2f}" if isinstance(latest_close, (int, float)) else "N/A"
    )

    lines = [
        f"- 종목:{name}({ticker}) | 최신 종가:{latest_close_text} | 기준일:{latest_date}"
    ]

    for label, days in period_map.items():
        required = days + 1
        if len(rows_sorted) < required:
            lines.append(f"  - {label}: 데이터가 충분하지 않습니다.")
            continue

        subset = rows_sorted[-required:]
        start_close = subset[0].get("close")
        end_close = subset[-1].get("close")
        if not isinstance(start_close, (int, float)) or not isinstance(
            end_close, (int, float)
        ):
            lines.append(f"  - {label}: 가격 정보가 불완전합니다.")
            continue
        if start_close == 0:
            lines.append(f"  - {label}: 기준가가 0이라 수익률을 계산할 수 없습니다.")
            continue

        change_pct = ((end_close - start_close) / start_close) * 100

        recent_slice = subset[-days:]
        volumes = [
            row.get("volume")
            for row in recent_slice
            if isinstance(row.get("volume"), (int, float))
        ]
        avg_volume = sum(volumes) / len(volumes) if volumes else None

        highs = [
            row.get("high")
            for row in recent_slice
            if isinstance(row.get("high"), (int, float))
        ]
        lows = [
            row.get("low")
            for row in recent_slice
            if isinstance(row.get("low"), (int, float))
        ]

        high_text = f"{max(highs):,.2f}" if highs else "N/A"
        low_text = f"{min(lows):,.2f}" if lows else "N/A"
        avg_volume_text = f"{avg_volume:,.0f}" if avg_volume is not None else "N/A"

        lines.append(
            f"  - {label}: 수익률 {change_pct:.2f}% | 고가 {high_text} | "
            f"저가 {low_text} | 평균 거래량 {avg_volume_text}"
        )

    return "\n".join(lines)


def split_response_by_period(text: str) -> dict[str, str]:
    sections = {period: "" for period in PERIOD_ORDER}
    current_period = None
    collected_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        matched_period = next(
            (period for period in PERIOD_ORDER if stripped.startswith(f"- {period}")),
            None,
        )
        if matched_period:
            if current_period is not None:
                sections[current_period] = "\n".join(collected_lines).strip()
            current_period = matched_period
            collected_lines = []
        elif current_period is not None:
            collected_lines.append(line)

    if current_period is not None:
        sections[current_period] = "\n".join(collected_lines).strip()

    return sections


def extract_verdicts(responses: dict[str, str]) -> dict[str, str]:
    verdicts: dict[str, str] = {}
    pattern = re.compile(r"판정:\s*(강력매수|매수|보유|매도|강력매도)")
    for period, text in responses.items():
        match = pattern.search(text)
        verdicts[period] = match.group(1) if match else ""
    return verdicts


sentiment_entries = load_json(RAWS_DIR / "sentiment_report.json")
top_movers_report = load_json(RAWS_DIR / "top_movers_auto.json")
chart_data = load_json(RAWS_DIR / "chart_data.json")

top_mover_details = top_movers_report.get("details", []) if isinstance(top_movers_report, dict) else []
if not top_mover_details:
    print("top_movers_auto.json 의 details 항목이 비어 있습니다.")
    sys.exit(0)


stocks_payload = {}

for detail in top_mover_details:
    stock_name = detail.get("name")
    ticker = detail.get("ticker")
    if not stock_name:
        continue

    sentiment_summary = summarize_sentiment_report(sentiment_entries, stock_name)
    top_movers_summary = summarize_top_movers(top_movers_report, stock_name, ticker)
    chart_item = find_chart_item(chart_data, stock_name, ticker)
    chart_summary = summarize_chart_item(chart_item)

    prompt = f"""
    지금부터 귀하는 데이터 기반의 냉철한 주식 분석가입니다.
    아래 자료를 분석하고 결과를 바탕으로 향후 주가 흐름에 대한 시나리오를 제시해 주십시오.

    대상 종목: {stock_name} ({ticker})

    자료 요약:
    감성 분석 요약:
    {sentiment_summary}

    상승 종목 요약:
    {top_movers_summary}

    차트 데이터 요약:
    {chart_summary}

    출력 규칙:
    1. 반드시 한글로 답변하고 높임말을 사용하십시오.
    2. 어떠한 마크업 언어도 사용하지 마십시오.
    3. 서두에 꾸밈말 없이 본론으로 바로 시작하십시오.
    4. 전체 답변은 `- 하루`, `- 일주일`, `- 한 달`, `- 6개월`, `- 일 년` 순서의 다섯 카테고리로 구성하십시오. 각 카테고리 이름 앞에는 하이픈(-)을 붙이십시오.
    5. 각 카테고리 내부에서는 다음 소제목을 순서대로 포함하십시오.
       - 주요 동향: 감성·수급·뉴스 관점에서 핵심 흐름을 요약하십시오.
       - 기술적 분석: 상승 종목과 수급 변화를 활용해 기술적 관점을 제시하십시오.
       - 차트 분석: 차트 데이터에서 해당 기간의 수익률, 고가·저가, 평균 거래량 등 수치를 활용해 설명하십시오.
       - 향후 시나리오: 들여쓴 하이픈(-)으로 긍정적 시나리오와 부정적 시나리오를 각각 제시하십시오.
       - 결론: 해당 기간 투자 관점을 요약하십시오.
       - 판정: 반드시 '판정: 강력매수/매수/보유/매도/강력매도' 형식으로 한 줄을 추가하십시오.
    6. 각 소제목 앞에는 하이픈(-)을 붙이되, 들여쓴 하이픈(-)은 향후 시나리오의 하위 항목에만 사용하십시오.
    7. 위 자료에서 확인 가능한 구체적 수치를 근거로 제시하십시오.
    """

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite",
    )

    generation_config = genai.types.GenerationConfig(
        temperature=0.3,
    )

    response = model.generate_content(
        prompt,
        generation_config=generation_config,
    )

    result_text = response.text if getattr(response, "text", None) else ""
    print(f"\n===== {stock_name} ({ticker}) =====")
    print(result_text)

    responses_by_period = split_response_by_period(result_text)
    verdicts_by_period = extract_verdicts(responses_by_period)

    stock_entry = {
        "ticker": ticker,
        "full_response": result_text,
        "periods": {
            period: {
                "text": responses_by_period.get(period, ""),
                "verdict": verdicts_by_period.get(period, ""),
            }
            for period in PERIOD_ORDER
        },
        "summaries": {
            "sentiment": sentiment_summary,
            "top_movers": top_movers_summary,
            "chart": chart_summary,
        },
    }

    stocks_payload[stock_name] = stock_entry


output_payload = {
    "generated_at": datetime.now().isoformat(),
    "model": "gemini-2.0-flash-lite",
    "stocks": stocks_payload,
}

output_path = RAWS_DIR / "Gemini_Api.json"
output_path.write_text(
    json.dumps(output_payload, ensure_ascii=False, indent=4),
    encoding="utf-8",
)

print(f"\n생성 결과를 '{output_path}'에 저장했습니다.")
