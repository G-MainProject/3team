import json
import os
import sys
from datetime import datetime
from pathlib import Path

import dotenv
import google.generativeai as genai


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent.parent / "data"
RAWS_DIR = DATA_DIR / "raws"
RAWS_DIR.mkdir(parents=True, exist_ok=True)


dotenv.load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


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


def summarize_sentiment_report(entries) -> str:
    lines = []
    for entry in entries:
        name = entry.get("stockName", "N/A")
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


def summarize_top_movers(report) -> str:
    lines = []
    date_value = report.get("date")
    market_value = report.get("market")
    header_parts = []
    if date_value:
        header_parts.append(f"기준일:{date_value}")
    if market_value:
        header_parts.append(f"시장:{market_value}")
    if header_parts:
        lines.append("- " + " | ".join(header_parts))

    for item in report.get("details", []) or []:
        name = item.get("name", "N/A")
        ticker = item.get("ticker", "N/A")
        change_pct = item.get("change_pct")
        price = item.get("current_price")
        change_display = (
            f"{change_pct:.2f}%" if isinstance(change_pct, (int, float)) else "N/A"
        )
        price_display = price if price is not None else "N/A"
        lines.append(
            f"  - 종목:{name}({ticker}) | 변동률:{change_display} | 현재가:{price_display}"
        )

    return "\n".join(lines) if lines else "자료 없음"


sentiment_entries = load_json(RAWS_DIR / "sentiment_report.json")
top_movers_report = load_json(RAWS_DIR / "top_movers_auto.json")
sentiment_summary = summarize_sentiment_report(sentiment_entries)
top_movers_summary = summarize_top_movers(top_movers_report)


prompt = f"""
지금부터 귀하는 데이터 기반의 냉철한 주식 분석가입니다.
아래 자료를 분석하고 결과를 바탕으로 향후 주가 흐름에 대한 시나리오를 제시해 주십시오.

답변 규칙:
1. 반드시 한글로 답변하고 높임말을 사용하십시오.
2. 어떠한 마크업 언어도 사용하지 마십시오. (*를 사용한 글씨 진하게 효과같은 것 사용X)
3. 서두에 꾸밈말 없이 본론으로 바로 시작하십시오.
4. 각 세션 제목 앞에는 항상 하이픈(-)을 붙이십시오.
5. 다음 세션을 순서대로 포함하십시오: 주요 동향 분석, 기술적 분석, 향후 시나리오, 결론.
6. 향후 시나리오 세션 아래에는 들여쓴 하이픈(-)으로 긍정적 시나리오와 부정적 시나리오를 각각 작성하십시오.
7. 데이터에서 확인 가능한 수치나 근거를 반드시 언급하십시오.
8. 감성 분석 요약과 상승 종목 요약에서 제시된 정보를 논리적 근거로 적극 활용하십시오.

감성 분석 요약:
{sentiment_summary}

상승 종목 요약:
{top_movers_summary}

추가 지시:
1. 주요 동향 분석: 데이터 기간 동안의 전반적인 가격 및 거래량 추세를 설명해 줘.
2. 기술적 분석: 5일 이동평균선을 계산하고 종가와 비교 분석해 줘.
3. 향후 시나리오: 이 분석을 기반으로 단기적으로 나타날 수 있는 긍정적 시나리오와 부정적 시나리오를 각각 제시해 줘.
4. 결론: 투자의견을 매수/매도로 제시해 줘.
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
print(result_text)

output_payload = {
    "generated_at": datetime.now().isoformat(),
    "model": model.model_name,
    "prompt": prompt,
    "response": result_text,
}

output_path = RAWS_DIR / "Gemini_Api.json"
output_path.write_text(
    json.dumps(output_payload, ensure_ascii=False, indent=4),
    encoding="utf-8",
)

print(f"\n생성 결과를 '{output_path}'에 저장했습니다.")
