import os
from io import StringIO

import pandas as pd
from konlpy.tag import Okt
import requests


class SentimentAnalyzer:
    """
    KoNLPy와 금융 뉴스 데이터를 이용한 뉴스 기사 감성 분석 클래스
    """

    def __init__(
        self,
        sentiment_data_source: str = 'finance_data.csv',
        *,
        sentiment_data_path: str | None = None,
        csv_encoding: str = 'utf-8',
        news_query: str = '삼성전자',
        news_api_key: str | None = 'b870e29967fc475db85ff307d655d284',
        news_page_size: int = 10,
    ) -> None:
        """
        분석기를 초기화하고 감성 사전을 로드한 뒤, NewsAPI에서 최신 기사를 가져온다.
        :param sentiment_data_source: 감성 사전 구축에 사용할 CSV 경로 또는 API URL (새 매개변수)
        :param sentiment_data_path: 기존 코드 호환을 위한 CSV 경로 별칭
        :param csv_encoding: 로컬 CSV 인코딩
        :param news_query: NewsAPI 검색어 기본값
        :param news_api_key: NewsAPI 키 (환경변수 NEWS_API_KEY가 지정되면 우선 사용)
        :param news_page_size: 가져올 기사 수(최대 100)
        """
        self.okt = Okt()

        if sentiment_data_path and sentiment_data_source != 'finance_data.csv' and sentiment_data_path != sentiment_data_source:
            raise ValueError('sentiment_data_source와 sentiment_data_path를 동시에 지정할 수 없습니다.')

        resolved_source = sentiment_data_path or sentiment_data_source
        self.sentiment_df = self._load_sentiment_dataframe(
            data_source=resolved_source,
            csv_encoding=csv_encoding,
        )
        self.word_dict = self._build_word_dict_from_dataframe(self.sentiment_df)

        env_news_api_key = os.getenv('NEWS_API_KEY')
        self.news_api_key = env_news_api_key if env_news_api_key else news_api_key
        self.news_query = news_query
        self.news_page_size = news_page_size
        self.news_df = pd.DataFrame()
        if self.news_api_key:
            self.news_df = self.fetch_news_from_api(
                query=self.news_query,
                api_key=self.news_api_key,
                page_size=self.news_page_size,
            )

    def _load_sentiment_dataframe(self, data_source: str, csv_encoding: str) -> pd.DataFrame:
        """감성 학습 데이터를 로컬 CSV 또는 API에서 로드한다."""
        if data_source.startswith('http://') or data_source.startswith('https://'):
            try:
                response = requests.get(data_source, timeout=10)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise RuntimeError(f'감성 데이터 API 요청 중 오류가 발생했습니다: {exc}') from exc

            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type or data_source.endswith('.json'):
                payload = response.json()
                if isinstance(payload, dict):
                    if 'data' in payload and isinstance(payload['data'], list):
                        payload = payload['data']
                    else:
                        payload = [payload]
                df = pd.DataFrame(payload)
            else:
                df = pd.read_csv(StringIO(response.text))
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            absolute_path = os.path.join(script_dir, data_source)
            try:
                df = pd.read_csv(absolute_path, encoding=csv_encoding)
            except FileNotFoundError as exc:
                raise FileNotFoundError(
                    f"감성 데이터 파일을 찾을 수 없습니다: '{absolute_path}'\n"
                    'finance_data.csv 파일을 폴더에 두거나 API URL을 지정해주세요.'
                ) from exc

        required_columns = {'labels', 'kor_sentence'}
        if not required_columns.issubset(df.columns):
            raise ValueError("감성 데이터에는 'labels'와 'kor_sentence' 열이 모두 포함되어야 합니다.")
        return df

    def _build_word_dict_from_dataframe(self, df: pd.DataFrame) -> dict[str, int]:
        """
        DataFrame에서 단어별 감성 점수 사전을 생성한다.
        긍정(positive)은 +1, 부정(negative)은 -1로 계산하여 단어별로 누적한다.
        """
        word_dict: dict[str, int] = {}
        label_map = {'positive': 1, 'negative': -1, 'neutral': 0}

        for _, row in df.iterrows():
            label = row['labels']
            sentence = row['kor_sentence']

            if not isinstance(sentence, str):
                continue

            score = label_map.get(label, 0)
            if score == 0:
                continue

            morphemes = self.okt.pos(sentence, stem=True, norm=True)
            for word, pos in morphemes:
                if pos in ['Noun', 'Verb', 'Adjective']:
                    word_dict[word] = word_dict.get(word, 0) + score

        return word_dict

    def fetch_news_from_api(self, query: str, api_key: str, page_size: int = 10) -> pd.DataFrame:
        """
        NewsAPI를 사용해 특정 검색어와 관련된 최신 한국어 뉴스를 가져온다.
        :param query: 검색할 키워드 또는 구문
        :param api_key: NewsAPI 키
        :param page_size: 가져올 기사 수(최대 100)
        :return: 뉴스 기사 제목과 본문이 담긴 DataFrame
        """
        params = {
            'q': query,
            'apiKey': api_key,
            'language': 'ko',
            'sortBy': 'publishedAt',
            'pageSize': page_size,
        }

        try:
            response = requests.get('https://newsapi.org/v2/everything', params=params, timeout=10)
            response.raise_for_status()
            news_data = response.json()

            if news_data.get('status') == 'ok':
                articles = news_data.get('articles', [])
                if not articles:
                    print('뉴스 기사를 찾을 수 없습니다.')
                    return pd.DataFrame()

                return pd.DataFrame(articles)[['title', 'content']]

            print(f"NewsAPI 오류: {news_data.get('message')}")
            return pd.DataFrame()

        except requests.exceptions.RequestException as exc:
            print(f'뉴스 API 요청 중 오류 발생: {exc}')
            return pd.DataFrame()

    def analyze_sentiment(self, text: str) -> tuple[str, float]:
        """
        주어진 텍스트의 감성을 분석하고, 점수와 분류 결과를 반환한다.
        :param text: 분석할 뉴스 기사 본문 (string)
        :return: (감성 분류, 감성 점수)
                 - 감성 분류: '긍정', '부정', '중립'
                 - 감성 점수: 계산된 수치
        """
        if not isinstance(text, str) or not text.strip():
            return '중립', 0.0

        morphemes = self.okt.pos(text, stem=True, norm=True)

        sentiment_score = 0
        word_count = 0

        for word, pos in morphemes:
            if pos in ['Noun', 'Verb', 'Adjective']:
                score = self.word_dict.get(word, 0)
                sentiment_score += score
                if score != 0:
                    word_count += 1

        normalized_score = sentiment_score / word_count if word_count else 0

        if normalized_score > 20:
            sentiment_class = '긍정'
        elif normalized_score < -20:
            sentiment_class = '부정'
        else:
            sentiment_class = '중립'

        return sentiment_class, normalized_score

    def extract_key_sentences(self, text: str, keywords: list[str]) -> list[str]:
        """
        주어진 텍스트에서 주요 키워드를 포함한 문장을 추출한다.
        :param text: 분석할 뉴스 본문 (뉴스 기사 본문)
        :param keywords: 찾아볼 주요 키워드 리스트
        :return: 주요 키워드를 포함한 문장의 리스트
        """
        sentences = text.split('.')

        key_sentences: list[str] = []
        for sentence in sentences:
            if any(keyword in sentence for keyword in keywords):
                key_sentences.append(sentence.strip() + '.')
        return key_sentences


if __name__ == '__main__':
    analyzer = SentimentAnalyzer()

    news_df = analyzer.news_df
    if news_df.empty:
        if analyzer.news_api_key:
            print('\n뉴스 기사를 가져오지 못해 분석을 건너뜁니다.')
            raise SystemExit(0)

        print('=' * 50)
        print('경고: NewsAPI 키가 설정되지 않았습니다.')
        print("환경변수 'NEWS_API_KEY'를 설정하거나 코드에 직접 API 키를 입력해주세요.")
        print('=' * 50)
        news_df = pd.DataFrame([
            {
                'title': '예시 뉴스: 기술주 호황',
                'content': '기술주가 신제품 개발 성공으로 실적이 크게 증가했다. 주가가 상승하며 투자자들의 기대감이 커지고 있다.',
            },
            {
                'title': '예시 뉴스: 바이오 회사 임상 실패',
                'content': '바이오 기업의 핵심 신약 후보가 임상에서 유의미한 결과를 내지 못했다. 투자심리가 얼어붙으며 주가가 급락했다.',
            },
        ])

    results = news_df['content'].apply(lambda text: analyzer.analyze_sentiment(text))
    news_df[['sentiment_class', 'sentiment_score']] = pd.DataFrame(results.tolist(), index=news_df.index)

    print(f"\n--- '{analyzer.news_query}' 관련 뉴스 감성 분석 결과 ---")
    print(news_df[['title', 'sentiment_class', 'sentiment_score']])