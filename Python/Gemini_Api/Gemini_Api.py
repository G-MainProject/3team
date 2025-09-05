import os
import dotenv
import google.generativeai as genai
import pandas as pd

# .env 파일에서 환경 변수를 불러옵니다.
dotenv.load_dotenv()

# API 키를 사용하여 라이브러리를 설정합니다.
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# 1. CSV 파일 읽기 (gemini_api.py와 같은 폴더에 있다고 가정)
try:
    df = pd.read_csv("주식데이터.csv")
    # 데이터프레임을 문자열로 변환
    stock_data_string = df.to_string()
except FileNotFoundError:
    print("오류: '주식데이터.csv' 파일을 찾을 수 없습니다. 파일 이름과 위치를 확인하세요.")
    exit()
# -----------------------------

# 2. 파일에서 읽은 데이터를 포함하여 프롬프트 구성
prompt = f"""
너는 데이터 기반의 냉철한 주식 분석가야.
아래 제공되는 주식 데이터를 분석하고, 그 결과를 바탕으로 향후 주가 흐름에 대한 시나리오를 제시해 줘.

답변 규칙
1. 항상 한글로 답변
2. 마크업언어 사용금지
3. 높임말 사용
4. 제공해주신 주식 데이터를 기반으로 냉철하게 분석한 결과를 말씀드립니다. 와 같은 꾸밈말 없이 바로 본론(결론)만 답변
5. 각 세션별로 하이픈을 넣고 답변을 작성해 내용 구분이 되도록 해줘
ex) 
- 향후 시나리오
이러한 분석을 바탕으로 단기적으로 나타날 수 있는 긍정적 시나리오와 부정적 시나리오를 각각 제시해 드립니다. 

    - 긍정적 시나리오
    최근 종가가 5일 이동평균선을 상회하며 상승 흐름을 보이고 있는 점은 단기적인 반등의 가능성을 ~~~
    
    - 부정적 시나리오
    현재 주가는 여전히 장기적인 하락 추세의 바닥권에 머물러 있으며, 최근의 반등은 ~~

**주식 데이터:**
{stock_data_string}

**수행 작업:**
1. 주요 동향 분석: 데이터 기간 동안의 전반적인 가격 및 거래량 추세를 설명해 줘.
2. 기술적 분석: 5일 이동평균선을 계산하고 종가와 비교 분석해 줘.
3. 향후 시나리오: 이 분석을 기반으로 단기적으로 나타날 수 있는 긍정적 시나리오와 부정적 시나리오를 각각 제시해 줘.
"""

# 원하는 설정을 포함하여 모델을 생성합니다.
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    # 모델 이름: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite

    # system_instruction="You are a cat. Your name is Neko."
)

# 생성 관련 설정을 정의합니다.
generation_config = genai.types.GenerationConfig(
    temperature=0.3
)

# 모델을 사용하여 콘텐츠를 생성합니다.
response = model.generate_content(
    # "How does AI work?",
    prompt,
    generation_config=generation_config
)

print(response.text)