import os
import sys
import urllib.request
import json
import requests
from bs4 import BeautifulSoup
import dotenv
from datetime import datetime, timedelta, timezone

# .env 파일에서 환경 변수를 불러옵니다.
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.env')
dotenv.load_dotenv(dotenv_path=dotenv_path)

# API 키를 사용하여 라이브러리를 설정합니다.
client_id = os.getenv("NAVER_CLIENT_ID")
client_secret = os.getenv("NAVER_CLIENT_SECRET")

if not client_id or not client_secret:
    print("오류: NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 환경 변수가 설정되지 않았습니다.")
    print(".env 파일을 확인해주세요.")
    sys.exit(1)

# 스크레이핑 실패 시 반환되는 메시지
FAIL_MESSAGE = "본문을 찾을 수 없습니다. (선택자 확인 필요)"

def safe_print(text):
    """
    콘솔에 출력할 때 발생할 수 있는 UnicodeEncodeError를 방지하기 위한 함수.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        # Windows의 cp949 콘솔 등에서 표시할 수 없는 문자는 '?'로 대체하여 출력
        print(text.encode(sys.stdout.encoding, 'replace').decode(sys.stdout.encoding))

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
            '#article-view-content-div',
            '#articleBody',
            '.article_body', '#articleBodyContents', '#dic_area', '.article-veiw-body', 
            '#article_txt', '.article-formatted-body', '.view_left',
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
            
            # --- 필터링 로직 --- #
            clean_lines = []
            base_filter_keywords = [
                '저작권자', '무단전재', '재배포 금지', '기자', 'ⓒ', 'Copyright', '▶', 
                '다른기사 보기', '페이스북', '트위터', '카카오스토리', '기사공유하기', '바로가기',
                '공유', '카카오', '이메일', 'URL', '기사저장', '댓글', '구독', '특파원', '='
            ]
            
            # 검색어가 필터 키워드에 있으면, 해당 검색어는 필터링에서 제외
            dynamic_filter_keywords = [kw for kw in base_filter_keywords if kw.lower() != search_word.lower()]

            email_filters = ['@', '.co.kr', '.com', '.net', '.kr']

            for line in unique_lines:
                # 동적으로 생성된 필터 키워드 리스트를 사용
                if not any(keyword in line for keyword in dynamic_filter_keywords) and not any(ef in line for ef in email_filters):
                    clean_lines.append(line)

            text_content = '\n'.join(clean_lines).strip()

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
    메인 실행 함수: 최근 1주일간, 최대 30개의 기사를 모을 때까지 실행
    """
    search_word = "삼성전자"
    encText = urllib.parse.quote(search_word)
    
    one_week_ago = datetime.now(timezone.utc) - timedelta(weeks=1)
    found_old_article = False

    successful_articles = []
    seen_links = set()
    start_index = 1
    display_count = 100

    print(f"'{search_word}'에 대한 뉴스 검색 시작 (최근 1주일, 최대 30건 목표)")

    while len(successful_articles) < 30 and not found_old_article and start_index <= 1000:
        url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display={display_count}&start={start_index}&sort=date"
        
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
                pub_date_str = item.get('pubDate')
                if not pub_date_str:
                    continue
                article_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')

                if article_date < one_week_ago:
                    found_old_article = True
                    print("--- 일주일이 지난 기사에 도달하여 검색을 중단합니다. ---")
                    break

                original_link = item.get('originallink') or item.get('link')
                if not original_link:
                    continue

                if original_link in seen_links:
                    continue
                seen_links.add(original_link)

                title = item.get('title')
                if not title:
                    continue

                if 'newsis.com' in original_link:
                    safe_print(f"- 건너뛰기 (미지원 사이트): {title.replace('<b>','').replace('</b>','')[:30]}...")
                    continue
                
                clean_title = BeautifulSoup(title, "html.parser").get_text()

                if search_word in clean_title:
                    content = get_news_content(original_link, search_word)

                    if content != FAIL_MESSAGE:
                        formatted_date = article_date.strftime('%Y-%m-%d')
                        successful_articles.append({
                            'title': clean_title,
                            'link': original_link,
                            'date': formatted_date,
                            'content': content
                        })
                        safe_print(f"- 성공: 총 {len(successful_articles)}/30 건 수집 완료 - '{clean_title[:30]}...'")
                
                if len(successful_articles) >= 30:
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
        safe_print(f"제목: {article['title']}")
        print(f"날짜: {article['date']}")
        print(f"링크: {article['link']}")
        print("\n--- 기사 본문 (스크레이핑) ---")
        safe_print(article['content'])
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()
