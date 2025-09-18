# 네이버 검색 API 예제 - 뉴스 검색 및 스크레이핑 (10개 성공 보장, 중복/불필요 내용/검색어 보호 제거)
import os
import sys
import urllib.request
import json
import requests
from bs4 import BeautifulSoup
import dotenv

# .env 파일에서 환경 변수를 불러옵니다.
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
dotenv.load_dotenv(dotenv_path=dotenv_path)

# API 키를 사용하여 라이브러리를 설정합니다.
client_id = os.getenv("NAVER_CLIENT_ID")
client_secret = os.getenv("NAVER_CLIENT_SECRET")

# 스크레이핑 실패 시 반환되는 메시지
FAIL_MESSAGE = "본문을 찾을 수 없습니다. (선택자 확인 필요)"

def get_news_content(link, search_word=""):
    """
    뉴스 기사 링크를 받아와 본문 내용을 스크레이핑하고 불필요한 내용을 제거하는 함수.
    검색어는 필터링 대상에서 제외한다.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
        response = requests.get(link, headers=headers, timeout=5)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        content_selectors = [
            '.article_body', '#articleBodyContents', '#dic_area', '.article-veiw-body', 
            '#article_txt', '.article-formatted-body', '.view_left', '#articeBody', 
            '#article_body', '[itemprop="articleBody"]', '.article_view'
        ]
        
        content = None
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                break
        
        if content:
            for tag in content.find_all(['script', 'style', 'figure', 'figcaption']):
                tag.decompose()
            
            lines = content.get_text(separator='\n', strip=True).split('\n')
            unique_lines = []
            seen_lines = set()
            for line in lines:
                if line and line not in seen_lines:
                    unique_lines.append(line)
                    seen_lines.add(line)
            
            # --- 필터링 로직 개선 --- #
            clean_lines = []
            base_filter_keywords = [
                '저작권자', '무단전재', '재배포 금지', '기자', 'ⓒ', 'Copyright', '▶', 
                '다른기사 보기', '페이스북', '트위터', '카카오스토리', '기사공유하기', '바로가기'
            ]
            
            # 검색어가 필터 키워드에 있으면, 해당 검색어는 필터링에서 제외
            dynamic_filter_keywords = [kw for kw in base_filter_keywords if kw.lower() != search_word.lower()]

            email_filters = ['@', '.co.kr', '.com', '.net', '.kr']

            for line in unique_lines:
                # 동적으로 생성된 필터 키워드 리스트를 사용
                if not any(keyword in line for keyword in dynamic_filter_keywords) and not any(ef in line for ef in email_filters):
                    clean_lines.append(line)

            text_content = '\n'.join(clean_lines)

            if len(text_content) > 100:
                return text_content
            else:
                return FAIL_MESSAGE
        else:
            return FAIL_MESSAGE

    except requests.exceptions.RequestException:
        return FAIL_MESSAGE
    except Exception:
        return FAIL_MESSAGE

def main():
    """
    메인 실행 함수: 성공한 기사 10개를 모을 때까지 실행
    """
    search_word = "페이스북" # 검색어 예시 변경
    encText = urllib.parse.quote(search_word)
    
    successful_articles = []
    seen_links = set()
    start_index = 1
    display_count = 20

    print(f"'{search_word}'에 대한 뉴스 검색 시작 (성공 10건 목표)")

    while len(successful_articles) < 10 and start_index <= 100:
        url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display={display_count}&start={start_index}"
        
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)
        
        try:
            response = urllib.request.urlopen(request)
            rescode = response.getcode()

            if rescode != 200:
                print(f"API Error Code: {rescode}")
                break

            response_body = response.read()
            news_data = json.loads(response_body.decode('utf-8'))

            if not news_data['items']:
                print("더 이상 검색 결과가 없습니다.")
                break

            for item in news_data['items']:
                original_link = item.get('originallink', item['link'])

                if original_link in seen_links:
                    continue
                seen_links.add(original_link)

                # get_news_content 호출 시 검색어 전달
                content = get_news_content(original_link, search_word)

                if content != FAIL_MESSAGE:
                    title = item['title'].replace("<b>", "").replace("</b>", "")
                    successful_articles.append({
                        'title': title,
                        'link': original_link,
                        'content': content
                    })
                    print(f"- 성공: {len(successful_articles)}/10 건 수집 완료 - '{title[:30]}...'")
                
                if len(successful_articles) >= 10:
                    break
            
            start_index += display_count

        except Exception as e:
            print(f"오류 발생: {e}")
            break

    print("\n" + "="*50)
    print(f"총 {len(successful_articles)}개의 기사 본문 수집 완료")
    print("="*50 + "\n")

    for i, article in enumerate(successful_articles):
        print(f"--- {i+1}번째 뉴스 기사 ---")
        print(f"제목: {article['title']}")
        print(f"링크: {article['link']}")
        print("\n--- 기사 본문 (스크레이핑) ---")
        print(article['content'])
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()