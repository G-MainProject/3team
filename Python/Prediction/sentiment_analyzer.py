import json
import pandas as pd
from konlpy.tag import Okt

class SentimentAnalyzer:
    """
    KoNLPy와 금융 뉴스 CSV 데이터를 이용한 뉴스 기사 감성 분석 클래스
    """
    def __init__(self, sentiment_data_path='finance_data.csv'):
        """
        분석기 초기화 및 감성 사전 로드
        :param sentiment_data_path: 금융 감성 데이터 (finance_data.csv) 파일 경로
        """
        import os
        self.okt = Okt()
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(script_dir, sentiment_data_path)

        try:
            # CSV 파일 로드
            df = pd.read_csv(absolute_path, encoding='utf-8')
        except FileNotFoundError:
            raise FileNotFoundError(
                f"감성 데이터 파일을 찾을 수 없습니다: '{absolute_path}'\n"
                "finance_data.csv 파일을 폴더에 저장해주세요."
            )
        
        # CSV 데이터로부터 단어-점수 사전을 구축합니다.
        self.word_dict = self._build_word_dict_from_csv(df)

    def _build_word_dict_from_csv(self, df):
        """
        DataFrame에서 단어별 감성 점수 사전을 생성합니다.
        긍정(positive)은 +1, 부정(negative)은 -1로 계산하여 단어별로 누적합니다.
        """
        word_dict = {}
        label_map = {'positive': 1, 'negative': -1, 'neutral': 0}

        for index, row in df.iterrows():
            label = row['labels']
            sentence = row['kor_sentence']
            
            if not isinstance(sentence, str):
                continue

            score = label_map.get(label, 0)
            if score == 0:
                continue

            # 문장에서 명사, 동사, 형용사 추출
            morphemes = self.okt.pos(sentence, stem=True, norm=True)
            for word, pos in morphemes:
                if pos in ['Noun', 'Verb', 'Adjective']:
                    word_dict[word] = word_dict.get(word, 0) + score
        
        return word_dict

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
        # 점수를 정규화 (단어 수로 나누어) 하여 일관된 스케일 유지
        normalized_score = sentiment_score / word_count if word_count > 0 else 0

        if normalized_score > 0.1:
            sentiment_class = '긍정'
        elif normalized_score < -0.1:
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
    # 클래스 인스턴스 생성 (새로운 CSV 파일 사용)
    analyzer = SentimentAnalyzer(sentiment_data_path='finance_data.csv')

    # 분석할 샘플 뉴스 데이터
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

    df = pd.DataFrame(sample_news)
    results = df['content'].apply(lambda text: analyzer.analyze_sentiment(text))
    df[['sentiment_class', 'sentiment_score']] = pd.DataFrame(results.tolist(), index=df.index)

    print("--- 감성 분석 결과 ---")
    print(df[['title', 'sentiment_class', 'sentiment_score']])