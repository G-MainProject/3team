# C:\Users\3CLASS_008\Documents\GitHub\3team\Python\Prediction\sentiment_analyzer.py
import json
import pandas as pd
from konlpy.tag import Okt

class SentimentAnalyzer:
    """
    KoNLPy와 KNU 한국어 감성사전을 이용한 뉴스 기사 감성 분석 클래스
    """
    def __init__(self, sentiment_dict_path='SentiWord_info.json'):
        """
        분석기 초기화 및 감성 사전 로드
        :param sentiment_dict_path: KNU 감성 사전 (SentiWord_info.json) 파일 경로
        """
        import os
        self.okt = Okt()
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(script_dir, sentiment_dict_path)

        try:
            with open(absolute_path, 'r', encoding='utf-8') as f:
                self.sentiment_dict = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"감성 사전 파일을 찾을 수 없습니다: '{absolute_path}'\n"
                "KNU 한국어 감성사전(SentiWord_info.json)을 다운로드하여 동일한 폴더에 저장해주세요."
            )
        
        # 감성 사전 포맷을 {단어: 점수} 형태로 변환
        self.word_dict = {item['word']: int(item['polarity']) for item in self.sentiment_dict}

    def analyze_sentiment(self, text):
        """
        주어진 텍스트의 감성을 분석하고, 점수와 분류 결과를 반환합니다.
        :param text: 분석할 뉴스 기사 본문 (string)
        :return: 튜플 (감성 분류, 감성 점수)
                 - 감성 분류: '긍정', '부정', '중립'
                 - 감성 점수: 계산된 수치
        """
        if not isinstance(text, str) or not text.strip():
            return '중립', 0

        # 1. 형태소 분석 (명사, 동사, 형용사 추출)
        morphemes = self.okt.pos(text, stem=True, norm=True)
        
        sentiment_score = 0
        word_count = 0
        
        # 2. 감성 점수 계산
        for word, pos in morphemes:
            if pos in ['Noun', 'Verb', 'Adjective']:
                # 감성 사전에 해당 단어가 있는지 확인
                score = self.word_dict.get(word, 0)
                sentiment_score += score
                if score != 0:
                    word_count += 1
        
        # 3. 감성 분류
        # 감성 단어가 하나도 없는 경우 '중립'으로 처리
        if word_count == 0:
            sentiment_class = '중립'
        elif sentiment_score > 0:
            sentiment_class = '긍정'
        elif sentiment_score < 0:
            sentiment_class = '부정'
        else:
            sentiment_class = '중립'
            
        return sentiment_class, sentiment_score

    def extract_key_sentences(self, text, keywords):
        """
        주어진 텍스트에서 핵심 키워드가 포함된 문장을 추출합니다.
        :param text: 분석할 원본 텍스트 (뉴스 기사 본문)
        :param keywords: 찾아낼 핵심 키워드 리스트
        :return: 핵심 키워드가 포함된 문장들의 리스트
        """
        # 텍스트를 문장 단위로 분리합니다.
        sentences = text.split('.')
        
        key_sentences = []
        for sentence in sentences:
            if any(keyword in sentence for keyword in keywords):
                key_sentences.append(sentence.strip() + '.')
        return key_sentences

# --- 예제 사용법 ---
if __name__ == '__main__':
    # 클래스 인스턴스 생성
    analyzer = SentimentAnalyzer()

    # 분석할 샘플 뉴스 데이터 (프로젝트 1단계에서 수집한 데이터라고 가정)
    sample_news = [
        {
            "title": "A전자, 신기술 개발로 역대 최고 실적 달성",
            "content": "A전자가 혁신적인 신기술 개발에 성공하여 시장의 예상을 뛰어넘는 분기 실적을 발표했습니다. 주가는 급등하며 투자자들의 기대감을 높였습니다."
        },
        {
            "title": "B바이오, 임상 3상 실패 소식에 주가 급락",
            "content": "B바이오의 주력 파이프라인이었던 신약 후보 물질이 임상 3상에서 유의미한 결과를 얻지 못했다는 소식이 전해졌습니다. 이에 대한 실망감으로 주가가 큰 폭으로 하락했습니다."
        },
        {
            "title": "C기업, 차기 주력 제품 공개 행사 예정",
            "content": "C기업은 다음 달 차세대 주력 제품을 공개하는 행사를 개최할 예정이라고 밝혔습니다. 시장은 이번 발표에 대해 관망하는 자세를 보이고 있습니다."
        }
    ]

    # 데이터프레임으로 변환
    df = pd.DataFrame(sample_news)

    # 각 뉴스에 대한 감성 분석 수행
    results = df['content'].apply(lambda text: analyzer.analyze_sentiment(text))
    
    # 결과(튜플)를 두 개의 새로운 컬럼으로 분리
    df[['sentiment_class', 'sentiment_score']] = pd.DataFrame(results.tolist(), index=df.index)

    print("--- 감성 분석 결과 ---")
    print(df[['title', 'sentiment_class', 'sentiment_score']])

    # 특정 기사 하나만 분석해보기
    print("\n--- 단일 기사 분석 예시 ---")
    single_text = "대규모 계약 체결 소식에 투자자들의 관심이 집중되고 있으며, 향후 실적 개선이 기대됩니다."
    s_class, s_score = analyzer.analyze_sentiment(single_text)
    print(f"기사 내용: {single_text}")
    print(f"감성 분류: {s_class}")
    print(f"감성 점수: {s_score}")

    # 핵심 문장 추출 예시
    print("\n--- 핵심 문장 추출 예시 ---")
    sample_content = "A전자가 혁신적인 신기술 개발에 성공하여 시장의 예상을 뛰어넘는 분기 실적을 발표했습니다. 이번 실적 발표는 주가에 긍정적인 영향을 미쳤습니다."
    sample_keywords = ["신기술", "실적"]
    key_sents = analyzer.extract_key_sentences(sample_content, sample_keywords)
    print(f"원본: {sample_content}")
    print(f"키워드: {sample_keywords}")
    print(f"추출된 문장: {key_sents}")
