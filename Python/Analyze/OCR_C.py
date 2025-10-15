import json
import os
import time
import logging
import io
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image

# --- 로깅 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 설정 (사용자 지정) ---
JSON_FILE_PATH = r"C:\A\B\ocrtest\ocrtest\asset\top_movers_auto.json"
OUTPUT_DIR = r"C:\Users\39200\OneDrive\문서\GitHub\3team\Python\Analyze\Asset\Img"

# --- 상수 ---
ZOOM_LEVEL = 2.6
FINANCIAL_TABLE_XPATH = '/html/body/div/form[1]/div[1]/div/div[2]/div[3]/div/div/div[14]/table[2]'
CAPTURE_MARGIN = 0
ROWS_TO_SKIP = 1

# --- WebDriver 설정 ---
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('window-size=1920x1080')
    options.add_argument("--disable-gpu")
    options.add_argument("lang=ko_KR")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    try:
        service = webdriver.chrome.service.Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.maximize_window()
        logging.info("WebDriver 초기화 및 창 최대화 완료.")
        return driver
    except WebDriverException as e:
        logging.error(f"WebDriver 초기화 중 오류 발생: {e}")
        return None

# --- 종목 데이터 로드 ---
def get_corp_data(json_file_path):
    if not os.path.exists(json_file_path):
        logging.error(f"'{json_file_path}' 파일을 찾을 수 없습니다.")
        return {}
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            return {item['ticker']: item['name'] for item in json_data.get('details', [])}
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"JSON 파일 파싱 중 오류 발생: {e}")
        return {}

# --- 재무제표 캡처 로직 (너비 및 마지막 행 문제 수정) ---
def capture_financial_statement(driver, corp_code, corp_name):
    logging.info(f"'{corp_name}' ({corp_code}) 재무제표 캡처 시작...")
    
    original_zoom = driver.execute_script("return document.body.style.zoom;")
    
    try:
        stock_url = f"https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd={corp_code}"
        driver.get(stock_url)
        wait = WebDriverWait(driver, 10)
        
        driver.execute_script(f"document.body.style.zoom='{ZOOM_LEVEL}'")
        time.sleep(1.0)
        logging.info(f"브라우저 줌 레벨 {int(ZOOM_LEVEL*100)}% 적용 완료.")

        financial_table_locator = (By.XPATH, FINANCIAL_TABLE_XPATH)
        financial_table = wait.until(EC.presence_of_element_located(financial_table_locator))
        
        rows = financial_table.find_elements(By.TAG_NAME, 'tr')
        
        # ⭐️ BUG FIX 1: 마지막 행이 포함되도록 `:-1` 슬라이싱 제거
        elements_to_capture = rows[ROWS_TO_SKIP:]
        
        captured_images = []
        logging.info(f"총 {len(rows)}개 행 중 {len(elements_to_capture)}개의 TR 요소를 캡처합니다.")
        
        if not elements_to_capture:
            logging.warning(f"'{corp_name}'에서 캡처할 실제 TR 요소를 찾을 수 없습니다. 스킵합니다.")
            return

        for i, element in enumerate(elements_to_capture):
            driver.execute_script("arguments[0].scrollIntoView({block: 'start'});", element)
            time.sleep(0.2)

            cells = element.find_elements(By.XPATH, ".//td | .//th")
            if not cells: continue

            cell_rects = [driver.execute_script("return arguments[0].getBoundingClientRect();", cell) for cell in cells]

            min_top = min(rect['top'] for rect in cell_rects)
            max_bottom = max(rect['bottom'] for rect in cell_rects)

            row_rect = driver.execute_script("return arguments[0].getBoundingClientRect();", element)
            
            # ⭐️ BUG FIX 2: 각 행의 실제 좌우 경계를 사용하여 너비 잘림 문제 해결
            left_px = row_rect['left'] - CAPTURE_MARGIN
            right_px = row_rect['right'] + CAPTURE_MARGIN # 고정 폭 대신 현재 행의 오른쪽 경계 사용
            
            top_px = min_top - CAPTURE_MARGIN
            bottom_px = max_bottom + CAPTURE_MARGIN
            
            # 줌이 적용된 최종 픽셀 좌표 (중복 계산 없음)
            left, top, right, bottom = left_px, top_px, right_px, bottom_px
            
            crop_area = (int(left), int(top), int(right), int(bottom))
            
            viewport_screenshot_png = driver.get_screenshot_as_png()
            with Image.open(io.BytesIO(viewport_screenshot_png)) as full_image:
                cropped_image = full_image.crop(crop_area)
                captured_images.append(cropped_image.copy())
            logging.info(f"데이터 TR 요소 {i}의 캡처 완료.")

        if not captured_images:
            logging.warning(f"'{corp_name}'에서 캡처된 이미지가 없어 최종 파일을 생성하지 않습니다.")
            return

        # 너비가 다른 행들을 병합하기 위해 최대 너비를 기준으로 캔버스 생성
        max_width = max(img.width for img in captured_images)
        total_height = sum(img.height for img in captured_images)
        
        combined_image = Image.new('RGB', (max_width, total_height))
        y_offset = 0
        for img in captured_images:
            combined_image.paste(img, (0, y_offset))
            y_offset += img.height
            img.close()
            
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        final_file_name = f"{corp_code}_financials.png"
        final_output_path = os.path.join(OUTPUT_DIR, final_file_name)
        combined_image.save(final_output_path, 'PNG')
        
        logging.info(f"고해상도 재무제표 이미지가 '{final_output_path}'에 저장되었습니다.")
            
    except Exception as e:
        logging.error(f"'{corp_code}' 캡처 중 오류 발생: {type(e).__name__} - {e}")
    finally:
        try:
            if original_zoom:
                driver.execute_script(f"document.body.style.zoom='{original_zoom}'")
            else:
                driver.execute_script("document.body.style.zoom='1.0'")
            time.sleep(0.2)
            logging.info("브라우저 줌 레벨 복구 완료.")
        except Exception as restore_e:
            logging.warning(f"브라우저 확대 복구 중 오류 발생: {restore_e}")

# --- 메인 실행 함수 ---
def main():
    driver = setup_driver()
    if not driver:
        return
        
    corp_codes = get_corp_data(JSON_FILE_PATH)
    if not corp_codes:
        logging.error("스크래핑을 진행할 종목 정보가 없습니다.")
        driver.quit()
        return

    try:
        for ticker, name in corp_codes.items():
            capture_financial_statement(driver, ticker, name)
            time.sleep(1)
    finally:
        if driver:
            driver.quit()
            logging.info("WebDriver 종료.")

if __name__ == "__main__":
    main()