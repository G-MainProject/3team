# c:\Users\3CLASS_008\Documents\GitHub\3team\Python\Prediction\main.py
import json
import os
from datetime import datetime

# 같은 폴더에 있는 모듈들을 임포트합니다.
from sentiment_analyzer import SentimentAnalyzer
from sales_predictor import SalesPredictor
from keyword_extractor import KeywordExtractor

def generate_comprehensive_report(stock_name, news_list, sales_data):
    """
    주어진 종목의 데이터로 모든 분석을 수행하고 종합 리포트를 생성합니다.
    
    :param stock_name: 분석할 종목명 (예: "A전자")
    :param news_list: 해당 종목 관련 뉴스 기사 딕셔너리 리스트 [{'title': ..., 'content': ...}, ...]
    :param sales_data: 해당 종목의 과거 분기별 매출 리스트
    :return: 분석 결과가 담긴 딕셔너리
    """
    print(f"'{stock_name}'에 대한 종합 분석을 시작합니다...")

    # --- 1. 감성 분석 수행 ---
    print("1. 뉴스 감성 분석 중...")
    # 감성 사전(SentiWord_info.json)이 이 파일과 같은 경로에 있다고 가정합니다.
    sentiment_analyzer = SentimentAnalyzer(sentiment_dict_path='SentiWord_info.json')
    
    total_sentiment_score = 0
    news_contents = [news['content'] for news in news_list]
    
    for content in news_contents:
        _, score = sentiment_analyzer.analyze_sentiment(content)
        total_sentiment_score += score
    
    avg_sentiment_score = total_sentiment_score / len(news_list) if news_list else 0
    
    # --- 2. 핵심 키워드 추출 ---
    print("2. 핵심 키워드 추출 중...")
    keyword_extractor = KeywordExtractor()
    full_news_text = " ".join(news_contents)
    keywords = keyword_extractor.extract_keywords(full_news_text, num_keywords=5)
    
    # --- 3. 매출 예측 ---
    print("3. 미래 매출 예측 중...")
    sales_predictor = SalesPredictor(look_back=4)
    sales_predictor.train(sales_data, verbose=0) # 학습 과정 로그는 생략
    last_4_quarters = sales_data[-4:]
    predicted_sales = sales_predictor.predict_next_quarter(last_4_quarters)
    
    # --- 4. 최종 리포트 생성 ---
    print("4. 최종 리포트 생성 중...")
    report = {
        "stockName": stock_name,
        "analysisDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sentimentAnalysis": {
            "averageScore": round(avg_sentiment_score, 2),
            "sentiment": "긍정" if avg_sentiment_score > 0.1 else "부정" if avg_sentiment_score < -0.1 else "중립"
        },
        "keywordAnalysis": {
            "topKeywords": keywords
        },
        "salesPrediction": {
            "lastQuartersData": last_4_quarters,
            "predictedNextQuarterSales": round(float(predicted_sales), 2)
        },
        "relatedNews": news_list
    }
    print("분석이 완료되었습니다.")
    return report

# --- 예제 사용법 ---
if __name__ == '__main__':
    # 1단계에서 특정 종목("A전자")에 대해 수집한 데이터라고 가정
    sample_news_data = [
        {"title": "A전자, 신기술 개발로 역대 최고 실적", "content": "A전자가 혁신적인 신기술 개발에 성공하여 시장의 예상을 뛰어넘는 분기 실적을 발표했습니다. 이번 실적 발표는 주가에 긍정적인 영향을 미쳤습니다."},
        {"title": "A전자, 차세대 반도체 특허 출원", "content": "A전자의 신기술 특허 출원 소식이 전해졌습니다. 해당 기술은 차세대 반도체 생산에 사용될 예정이며, 대규모 계약으로 이어질 가능성이 높습니다."}
    ]
    sample_sales_data = [100, 110, 105, 120, 130, 145, 135, 150, 160, 170, 165, 180]

    final_report = generate_comprehensive_report("A전자", sample_news_data, sample_sales_data)

    # 결과를 JSON 형태로 예쁘게 출력
    print("\n--- 최종 분석 리포트 ---")
    print(json.dumps(final_report, indent=4, ensure_ascii=False))