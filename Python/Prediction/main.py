"""
data 폴더의 크롤링된 엑셀 파일들을 읽어와 분석 리포트를 생성하는 스크립트.
"""
import json
import os
import glob
from datetime import datetime
from collections import Counter
import pandas as pd

from sentiment_analyzer import SentimentAnalyzer
from keyword_extractor import KeywordExtractor


def generate_comprehensive_report(stock_name, news_list, resources_dir="."):
    """
    종합 리포트를 생성한다.
    - 감성 분석(뉴스 본문 목록 기반)
    - 키워드 추출(문서 전체 텍스트 합본 기반)
    """
    print(f"[Start] Analysis for '{stock_name}'")

    # 1) 감성 분석
    print("1) Sentiment analysis..")
    senti_path = os.path.join(resources_dir, 'finance_data.csv')
    sentiment_analyzer = SentimentAnalyzer(sentiment_data_path=senti_path)

    total_sentiment_score = 0.0
    sentiment_counts = Counter()
    news_contents = []

    for news in news_list:
        content = str(news.get('content', ''))
        news_contents.append(content)
        sentiment_class, score = sentiment_analyzer.analyze_sentiment(content)
        total_sentiment_score += score
        # 긍정/부정/중립 카운트
        if sentiment_class == '긍정':
            sentiment_counts['positive'] += 1
        elif sentiment_class == '부정':
            sentiment_counts['negative'] += 1
        else:
            sentiment_counts['neutral'] += 1

    avg_sentiment_score = total_sentiment_score / len(news_list) if news_list else 0.0

    # 2) 키워드 추출
    print("2) Keyword extraction..")
    keyword_extractor = KeywordExtractor()
    full_news_text = " ".join(news_contents)
    detailed_keywords = keyword_extractor.extract_keywords(full_news_text, num_keywords=50, return_detail=True)
    
    # stockName 및 그 일부를 키워드에서 필터링
    filtered_keywords = []
    for item in detailed_keywords:
        keyword = item['keyword']
        # stock_name이나 키워드가 다른 한 쪽에 포함되면 제외 (e.g., stock_name="삼성전자", keyword="삼성")
        if stock_name not in keyword and keyword not in stock_name:
            filtered_keywords.append(item)

    # 워드 클라우드 데이터 생성: {"키워드": 빈도수}
    word_cloud_data = {item['keyword']: item.get('frequency', 1) for item in filtered_keywords}

    # 3) 최종 리포트 조립
    print("3) Building report..")
    report = {
        "stockName": stock_name,
        "analysisDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sentimentAnalysis": {
            "averageScore": round(avg_sentiment_score, 2),
            "overallSentiment": (
                "positive" if avg_sentiment_score > 0.1 else (
                    "negative" if avg_sentiment_score < -0.1 else "neutral"
                )
            ),
            "sentimentDistribution": dict(sentiment_counts)
        },
        "keywordAnalysis": {
            "wordCloud": word_cloud_data
        },
        "relatedNews": news_list,
    }

    print(f"[Done] Analysis for '{stock_name}' complete.")
    return report


def _normalize_header(h: str) -> str:
    return (h or "").strip().lower().replace(" ", "")


def _pick_col(df, candidates):
    norm_cols = {_normalize_header(c): c for c in df.columns}
    for cand in candidates:
        key = _normalize_header(cand)
        if key in norm_cols:
            return norm_cols[key]
    return None


def _normalize_date_value(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    try:
        s = str(v).strip().replace(".", "-")
        dt = pd.to_datetime(s, errors='coerce')
        if pd.notna(dt):
            return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        if isinstance(v, (int, float)) and not pd.isna(v):
            base = pd.Timestamp('1899-12-30')
            dt = base + pd.to_timedelta(int(v), unit='D')
            return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    return str(v)


def load_news_from_excel_file(file_path: str, max_rows_per_sheet: int | None = None):
    """
    단일 엑셀 파일에서 표준 뉴스 포맷 리스트를 로드한다.
    """
    news_items = []
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return news_items

    try:
        xls = pd.ExcelFile(file_path)
        for sheet in xls.sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet, dtype=str)
                if df.empty:
                    continue
                
                df.columns = [str(c).strip() for c in df.columns]
                title_col = _pick_col(df, ['제목', '타이틀', '헤드라인', 'title'])
                broker_col = _pick_col(df, ['증권사', '출처', '기관', '회사'])
                date_col = _pick_col(df, ['날짜', '일자', '작성일', '보고서일', 'date'])
                content_col = _pick_col(df, ['내용', '본문', '요약', '텍스트', '기사내용', 'content'])

                if not title_col and not content_col:
                    continue

                take_df = df[[c for c in [title_col, broker_col, date_col, content_col] if c]].copy()
                if date_col and date_col in take_df.columns:
                    take_df[date_col] = take_df[date_col].map(_normalize_date_value)
                if max_rows_per_sheet:
                    take_df = take_df.head(max_rows_per_sheet)

                for _, row in take_df.iterrows():
                    title = str(row.get(title_col, '') or '').strip()
                    content = str(row.get(content_col, '') or '').strip()
                    source = str(row.get(broker_col, '') or '').strip()
                    date_val = str(row.get(date_col, '') or '').strip()
                    if not title and not content:
                        continue
                    news_items.append({
                        'title': title,
                        'content': content or title,
                        'source': source,
                        'date': date_val,
                    })
            except Exception as se:
                print(f"Warning: failed to parse sheet '{sheet}' in {file_path}: {se}")
    except Exception as e:
        print(f"Warning: failed to open Excel file {file_path}: {e}")
    return news_items


def main():
    """
    메인 실행 함수
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(os.path.join(script_dir, '..', '..', 'data'))
    output_dir = script_dir

    report_files = glob.glob(os.path.join(data_dir, "리포트_*.xlsx"))

    if not report_files:
        print(f"No report files found in '{data_dir}'. (e.g., 리포트_신한투자증권.xlsx)")
        return

    print(f"Found {len(report_files)} report files to analyze.")

    all_reports = []
    for report_file in report_files:
        base_name = os.path.splitext(os.path.basename(report_file))[0]
        if base_name.startswith('리포트_'):
            company_name = base_name[4:]
        else:
            company_name = base_name

        print(f"\n--- Processing: {company_name} ---")
        
        news_data = load_news_from_excel_file(report_file)
        
        if not news_data:
            print(f"No news data could be loaded from '{report_file}'. Skipping.")
            continue

        report = generate_comprehensive_report(company_name, news_data, resources_dir=script_dir)
        all_reports.append(report)

    # 모든 리포트를 final_report.json 파일에 저장
    output_path = os.path.join(output_dir, "final_report.json")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_reports, f, ensure_ascii=False, indent=4)
        print(f"\nSuccessfully saved all reports to '{output_path}'")
    except Exception as e:
        print(f"Error saving final report to '{output_path}': {e}")

if __name__ == '__main__':
    main()
