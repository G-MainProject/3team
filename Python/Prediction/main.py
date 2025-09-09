"""
뉴스 크롤링 엑셀(.xlsx/.xls/.xlsm)을 읽어 미리보기/JSON 저장/분석까지 수행하는 실행 스크립트.

주요 기능
- 크롤링 엑셀 미리보기: 폴더 안의 모든 엑셀 파일을 순회하며 시트별 상위 N행을 출력
- 엑셀 → 뉴스 리스트 변환: (제목/증권사/날짜/내용) 형식의 행을 표준 뉴스 포맷으로 로드
- 선택적으로 JSON으로 저장(기존 파일과 병합 가능)
- 뉴스 감성/키워드 분석 및 (선택) 매출 예측 리포트 생성

실행 예시(PowerShell)
- 미리보기만:  python Python/Prediction/main.py --excel-dir "C:\\path\\to\\excel" --skip-analysis
- 엑셀을 분석 입력으로 사용:  python Python/Prediction/main.py --excel-news-dir "C:\\path\\to\\excel"
- 엑셀을 news_data.json으로 저장:  python Python/Prediction/main.py --excel-news-dir "C:\\path\\to\\excel" --write-news-json "C:\\Users\\...\\news_data.json" --news-stock-code 005930 --merge-news-json
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

import pandas as pd

from sentiment_analyzer import SentimentAnalyzer
from sales_predictor import SalesPredictor
from keyword_extractor import KeywordExtractor


def generate_comprehensive_report(stock_name, news_list, sales_data=None, resources_dir="."):
    """
    종합 리포트를 생성한다.
    - 감성 분석(뉴스 본문 목록 기반)
    - 키워드 추출(문서 전체 텍스트 합본 기반)
    - (선택) 매출 예측: 판매 시계열이 제공된 경우에만 수행
    """
    print(f"[Start] Analysis for '{stock_name}'")

    # 1) 감성 분석: 뉴스 본문을 순회하며 점수를 합산/평균화
    print("1) Sentiment analysis..")
    senti_path = os.path.join(resources_dir, 'SentiWord_info.json')
    sentiment_analyzer = SentimentAnalyzer(sentiment_dict_path=senti_path)

    total_sentiment_score = 0.0
    news_contents = [str(news.get('content', '')) for news in news_list]
    for content in news_contents:
        _, score = sentiment_analyzer.analyze_sentiment(content)
        total_sentiment_score += score
    avg_sentiment_score = total_sentiment_score / len(news_list) if news_list else 0.0

    # 2) 키워드 추출: 전체 본문을 하나로 합쳐 상위 키워드 계산
    print("2) Keyword extraction..")
    keyword_extractor = KeywordExtractor()
    full_news_text = " ".join(news_contents)
    detailed_keywords = keyword_extractor.extract_keywords(full_news_text, num_keywords=20, return_detail=True)

    # 3) (선택) 매출 예측: 최소 5개 이상의 시계열이 있을 때만 LSTM 기반 예측 수행
    print("3) Sales prediction..")
    sales_section = None
    if sales_data and isinstance(sales_data, (list, tuple)) and len(sales_data) >= 5:
        sales_predictor = SalesPredictor(look_back=4)
        try:
            sales_predictor.train(sales_data, verbose=0)
            last_4_quarters = list(sales_data[-4:])
            predicted_sales = sales_predictor.predict_next_quarter(last_4_quarters)
            sales_section = {
                "lastQuartersData": last_4_quarters,
                "predictedNextQuarterSales": round(float(predicted_sales), 2)
            }
        except Exception as e:
            print(f"Warning: sales prediction failed: {e}")

    # 4) 최종 리포트 조립
    print("4) Building report..")
    report = {
        "stockName": stock_name,
        "analysisDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sentimentAnalysis": {
            "averageScore": round(avg_sentiment_score, 2),
            "sentiment": (
                "positive" if avg_sentiment_score > 0.1 else (
                    "negative" if avg_sentiment_score < -0.1 else "neutral"
                )
            ),
        },
        "keywordAnalysis": {
            "topKeywords": [item['keyword'] for item in detailed_keywords[:5]],
            "keywordDetails": detailed_keywords,
        },
        "relatedNews": news_list,
    }
    if sales_section is not None:
        report["salesPrediction"] = sales_section

    print("[Done] Analysis complete.")
    return report


def _load_stocks_from_csv(csv_path):
    """
    종목 목록 CSV를 읽어 (주식코드, 종목명) 튜플 리스트로 반환한다.
    - CSV 컬럼명 예: stock_code, stock_name
    - 파일이 없으면 빈 리스트 반환(호출부에서 news_data.json 키로 대체)
    """
    items = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get('stock_code') or '').strip()
                name = (row.get('stock_name') or '').strip()
                if code:
                    items.append((code, name or code))
    except FileNotFoundError:
        print(f"Warning: '{csv_path}' not found. Falling back to news_data.json keys.")
    return items


def _maybe_load_sales_series(script_dir, stock_code):
    """
    판매 시계열 CSV를 찾아 숫자 리스트로 반환한다. 없으면 None.
    - 탐색 순서: sales_<code>.csv, <code>_sales.csv, sales_data.csv
    - 헤더가 있어도 무시하고 모든 숫자 셀을 수집
    """
    candidates = [
        os.path.join(script_dir, f'sales_{stock_code}.csv'),
        os.path.join(script_dir, f'{stock_code}_sales.csv'),
        os.path.join(script_dir, 'sales_data.csv'),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                series = []
                with open(path, 'r', encoding='utf-8') as f:
                    r = csv.reader(f)
                    _ = next(r, None)  # optional header
                    for row in r:
                        for cell in row:
                            cell = cell.strip()
                            if not cell:
                                continue
                            try:
                                series.append(float(cell))
                            except ValueError:
                                pass
                if series:
                    return series
            except Exception as e:
                print(f"Warning: failed to load sales data ({path}): {e}")
    return None


def _normalize_header(h: str) -> str:
    """헤더 문자열을 소문자/공백제거 형태로 정규화"""
    return (h or "").strip().lower().replace(" ", "")


def _pick_col(df, candidates):
    """
    후보 컬럼명 리스트 중 실제 DataFrame 컬럼과 가장 잘 매칭되는 것을 선택한다.
    - 비교는 _normalize_header 로 전처리하여 느슨하게 수행
    - 없으면 None 반환
    """
    norm_cols = { _normalize_header(c): c for c in df.columns }
    for cand in candidates:
        key = _normalize_header(cand)
        if key in norm_cols:
            return norm_cols[key]
    return None


def _normalize_date_value(v):
    """
    날짜 값을 YYYY-MM-DD 문자열로 정규화 시도.
    - 문자열: 2025.09.09 / 2025-09-09 등은 pandas.to_datetime으로 처리
    - 숫자: 엑셀 일련번호(1899-12-30 기준)로 가정하여 변환 시도
    - 실패 시 원래 값을 문자열로 반환
    """
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    try:
        # Try parsing common string formats like '2025.09.09' or '2025-09-09'
        s = str(v).strip().replace(".", "-")
        dt = pd.to_datetime(s, errors='coerce')
        if pd.notna(dt):
            return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    # Excel serial dates (numeric)
    try:
        if isinstance(v, (int, float)) and not pd.isna(v):
            base = pd.Timestamp('1899-12-30')
            dt = base + pd.to_timedelta(int(v), unit='D')
            return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    return str(v)


def preview_crawled_excel(dir_path: str, preview_rows: int = 5):
    """
    크롤링 엑셀(제목/증권사/날짜/내용)을 읽어 시트별 상위 N행을 출력한다.
    - 컬럼명이 약간 달라도 후보 목록을 기준으로 자동 매핑
    - 단순 확인용 미리보기 기능이며, 저장/분석은 수행하지 않음
    """
    if not os.path.isdir(dir_path):
        print(f"Excel preview skipped: not a directory: {dir_path}")
        return

    print(f"\n[Excel Preview - Crawled Format] dir: {dir_path}")
    excel_exts = {'.xlsx', '.xls', '.xlsm'}
    found = False
    for root, _, files in os.walk(dir_path):
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext.lower() not in excel_exts:
                continue
            found = True
            fpath = os.path.join(root, fname)
            try:
                xls = pd.ExcelFile(fpath)
                for sheet in xls.sheet_names:
                    try:
                        df = pd.read_excel(fpath, sheet_name=sheet, dtype=str)
                        if df.empty:
                            continue
                        # Trim/normalize headers
                        df.columns = [str(c).strip() for c in df.columns]
                        title_col = _pick_col(df, ['제목', '타이틀', '헤드라인', 'title'])
                        broker_col = _pick_col(df, ['증권사', '출처', '기관', '회사'])
                        date_col = _pick_col(df, ['날짜', '일자', '작성일', '보고서일', 'date'])
                        content_col = _pick_col(df, ['내용', '본문', '요약', '텍스트', '기사내용'])

                        sel = []
                        if title_col: sel.append(title_col)
                        if broker_col: sel.append(broker_col)
                        if date_col: sel.append(date_col)
                        if content_col: sel.append(content_col)
                        if not sel:
                            continue

                        out = df[sel].head(preview_rows).copy()
                        if date_col and date_col in out.columns:
                            out[date_col] = out[date_col].map(_normalize_date_value)

                        print(f"\n- File: {fpath} | Sheet: {sheet}")
                        print(out)
                    except Exception as se:
                        print(f"  Warning: failed to read sheet ({sheet}): {se}")
            except Exception as e:
                print(f"Warning: failed to load Excel file ({fpath}): {e}")

    if not found:
        print("No Excel files found.")


def load_news_from_crawled_excel(dir_path: str, max_rows_per_sheet: int | None = None):
    """
    크롤링 엑셀 폴더를 표준 뉴스 포맷 리스트로 변환한다.
    - 반환 형식: [{'title','content','date','source','file','sheet'}, ...]
    - 시트별로 (제목/증권사/날짜/내용) 컬럼을 찾아 행을 뉴스 아이템으로 변환
    - max_rows_per_sheet 지정 시 각 시트에서 해당 개수만 읽음
    """
    news_items = []
    if not os.path.isdir(dir_path):
        print(f"Excel news load skipped: not a directory: {dir_path}")
        return news_items

    excel_exts = {'.xlsx', '.xls', '.xlsm'}
    for root, _, files in os.walk(dir_path):
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext.lower() not in excel_exts:
                continue
            fpath = os.path.join(root, fname)
            try:
                xls = pd.ExcelFile(fpath)
                for sheet in xls.sheet_names:
                    try:
                        df = pd.read_excel(fpath, sheet_name=sheet, dtype=str)
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
                                'file': fpath,
                                'sheet': sheet,
                            })
                    except Exception as se:
                        print(f"Warning: failed to parse sheet for news ({sheet}) in {fpath}: {se}")
            except Exception as e:
                print(f"Warning: failed to open Excel file ({fpath}): {e}")
    return news_items


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    news_data_path = os.path.join(script_dir, 'news_data.json')
    stocks_csv_path = os.path.join(script_dir, 'stocks_to_analyze.csv')

    # 명령행 인자 정의: 미리보기/엑셀 로드/JSON 저장/분석 실행을 제어
    parser = argparse.ArgumentParser(description="Run news analysis and optionally preview/load crawled Excel files.")
    parser.add_argument("--excel-dir", dest="excel_dir", default=None, help="Directory containing crawled Excel files (제목/증권사/날짜/내용)")
    parser.add_argument("--excel-preview-rows", dest="excel_preview_rows", type=int, default=5, help="Number of rows to preview per sheet")
    parser.add_argument("--skip-analysis", action="store_true", help="Only preview Excel files and exit")
    parser.add_argument("--excel-news-dir", dest="excel_news_dir", default=None, help="Use crawled Excel files as news input instead of news_data.json")
    parser.add_argument("--excel-news-max-rows", dest="excel_news_max_rows", type=int, default=None, help="Max rows to read per sheet for news input")
    parser.add_argument("--write-news-json", dest="write_news_json", default=None, help="If set with --excel-news-dir, save loaded news to this JSON path")
    parser.add_argument("--news-stock-code", dest="news_stock_code", default=None, help="Optional stock code key to wrap Excel news under (e.g., 005930)")
    parser.add_argument("--merge-news-json", dest="merge_news_json", action="store_true", help="Merge into existing JSON if it exists")
    args = parser.parse_args()

    # 엑셀 미리보기(선택): 폴더·시트를 순회하며 상위 N행만 출력하고, --skip-analysis면 종료
    if args.excel_dir:
        preview_crawled_excel(args.excel_dir, preview_rows=args.excel_preview_rows)
        if args.skip_analysis:
            sys.exit(0)

    if args.excel_news_dir:
        # 엑셀 폴더에서 뉴스 행을 직접 로드하여 표준 포맷으로 변환
        excel_news = load_news_from_crawled_excel(args.excel_news_dir, max_rows_per_sheet=args.excel_news_max_rows)
        if not excel_news:
            print("No news rows could be loaded from the Excel directory.")
            raise SystemExit(1)

        # 옵션: 로드한 뉴스를 JSON 파일로 저장(필요 시 기존과 병합)
        if args.write_news_json:
            def _save_json(news_items, path, stock_code=None, merge=False):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                payload = None
                if stock_code:
                    # 주식코드 하위 키로 감싸서 저장(예: {"005930": [...]})
                    payload = {stock_code: news_items}
                    if merge and os.path.exists(path):
                        try:
                            with open(path, 'r', encoding='utf-8') as rf:
                                existing = json.load(rf)
                            if isinstance(existing, dict):
                                existing.setdefault(stock_code, [])
                                existing[stock_code].extend(news_items)
                                payload = existing
                        except Exception as e:
                            print(f"Warning: failed to merge existing JSON: {e}")
                else:
                    payload = news_items
                    if merge and os.path.exists(path):
                        try:
                            with open(path, 'r', encoding='utf-8') as rf:
                                existing = json.load(rf)
                            if isinstance(existing, list):
                                existing.extend(news_items)
                                payload = existing
                        except Exception as e:
                            print(f"Warning: failed to merge existing JSON: {e}")

                with open(path, 'w', encoding='utf-8') as wf:
                    json.dump(payload, wf, ensure_ascii=False, indent=4)
                print(f"Saved Excel news to JSON: {path}")

            _save_json(excel_news, args.write_news_json, stock_code=args.news_stock_code, merge=args.merge_news_json)

        # 로드한 엑셀 뉴스 전체를 하나의 문서 집합으로 간단 분석 실행
        report = generate_comprehensive_report("Crawled Excel", excel_news, sales_data=None, resources_dir=script_dir)
        print("\n--- Crawled Excel Final Report ---")
        print(json.dumps(report, indent=4, ensure_ascii=False))
        print("-" * 50)
    else:
        # news_data.json을 사용하여 종목별 분석 실행
        try:
            with open(news_data_path, 'r', encoding='utf-8') as f:
                all_news_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: '{news_data_path}' not found.")
            raise SystemExit(1)

        stocks = _load_stocks_from_csv(stocks_csv_path)
        if not stocks:
            stocks = [(code, code) for code in all_news_data.keys()]

        for stock_code, stock_name in stocks:
            if stock_code not in all_news_data:
                print(f"\n--- {stock_name}({stock_code}) has no related news in 'news_data.json'. ---")
                continue

            stock_news_data = all_news_data[stock_code]
            sales_series = _maybe_load_sales_series(script_dir, stock_code)
            report = generate_comprehensive_report(stock_name, stock_news_data, sales_series, resources_dir=script_dir)

            print(f"\n--- {stock_name}({stock_code}) Final Report ---")
            print(json.dumps(report, indent=4, ensure_ascii=False))
            print("-" * 50)
