from sklearn.feature_extraction.text import TfidfVectorizer

class KeywordExtractor:
    def __init__(self):
        # TfidfVectorizer를 초기화합니다. 한국어 불용어를 사용하려면 'english' 대신 별도의 불용어 리스트를 지정해야 합니다.
        self.vectorizer = TfidfVectorizer(stop_words='english')

    def extract_keywords(self, text, num_keywords=5):
        """
        주어진 텍스트에서 키워드를 추출합니다.

        :param text: 키워드를 추출할 텍스트
        :param num_keywords: 추출할 키워드의 수
        :return: 추출된 키워드 리스트
        """
        if not text or not isinstance(text, str):
            return []
            
        try:
            # 텍스트를 공백으로 분리하여 단어 리스트로 만듭니다.
            # 실제 사용 시에는 형태소 분석기(e.g., Okt, Mecab)를 사용하는 것이 더 좋습니다.
            corpus = [text]
            
            # TF-IDF 행렬을 생성합니다.
            tfidf_matrix = self.vectorizer.fit_transform(corpus)
            
            # 단어 목록을 가져옵니다.
            feature_names = self.vectorizer.get_feature_names_out()
            
            # 문서의 TF-IDF 점수를 가져옵니다.
            scores = tfidf_matrix.toarray().flatten()
            
            # 점수가 가장 높은 키워드의 인덱스를 가져옵니다.
            top_keyword_indices = scores.argsort()[-num_keywords:][::-1]
            
            # 키워드를 가져옵니다.
            keywords = [feature_names[i] for i in top_keyword_indices]
            
            return keywords
        except Exception as e:
            print(f"키워드 추출 중 오류 발생: {e}")
            return []

