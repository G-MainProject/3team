import easyocr
import cv2
import os
import re
import csv
import numpy as np
from OCR_D import replace_words

def preprocess_for_numbers(img):
    """
    숫자 인식률을 높이기 위해 이미지를 전처리하는 함수입니다.
    - 그레이스케일 변환
    - 샤프닝 필터 적용
    - 적응형 이진화
    - 이미지 2배 확대
    """
    try:
        # 이미지를 흑백(그레이스케일)으로 변환
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 샤프닝(선명화)을 위한 커널 정의 및 적용
        sharpening_kernel = np.array([[-1, -1, -1],
                                      [-1,  9, -1],
                                      [-1, -1, -1]])
        sharpened = cv2.filter2D(gray, -1, sharpening_kernel)
        
        # 적응형 이진화 적용 (이미지의 밝기 변화에 따라 유연하게 텍스트를 분리)
        processed = cv2.adaptiveThreshold(
            sharpened, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            11, 2
        )
        
        # 이미지를 2배 확대하여 작은 텍스트의 인식률을 향상
        resized = cv2.resize(processed, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        
        return resized
    except Exception as e:
        print(f"이미지 전처리 중 오류가 발생했습니다: {e}")
        return None

def clean_numeric_text(text):
    """
    숫자 문자열에서 쉼표(,)와 하이픈(-)을 제외한 모든 특수문자를 제거합니다.
    """
    # 쉼표를 제거하고 숫자, 하이픈(-), 점(.)만 남기고 모두 제거
    return re.sub(r'[^0-9.\-]', '', text.replace(',', ''))

def format_number_with_commas(text):
    """
    하이픈을 포함한 숫자 문자열에 쉼표로 천 단위 구분 기호를 추가하고, 
    정수일 경우 소수점 이하는 제거합니다.
    """
    # 텍스트에서 쉼표를 제거합니다.
    cleaned_num_str = text.replace(',', '')
    
    try:
        # 하이픈을 임시로 제거하고 숫자로 변환합니다.
        number = float(cleaned_num_str.replace('-', ''))
        
        # .0을 제거하기 위해 정수인지 확인
        if number.is_integer():
            formatted_text = f'{int(number):,}'
        else:
            formatted_text = f'{number:,}'
        
        # 원래 텍스트에 하이픈이 있었는지 확인
        if '-' in text:
            # 음수 포맷팅
            return f'-{formatted_text}'
        
        return formatted_text
    except ValueError:
        return text

def is_numeric_text(text):
    """
    텍스트가 숫자만 포함하는지 판별합니다.
    - 한글이 포함된 경우 (예: '제10기') 숫자로 인식하지 않습니다.
    """
    text = text.strip()
    if re.search(r'[가-힣]', text):
        return False
    # 숫자, 하이픈, 점, 쉼표, 괄호, 공백만 남기고 검사
    temp_text = re.sub(r'[^0-9.\-(),]+', '', text)
    if not temp_text:
        return False
    # 괄호, 쉼표를 제거하고 float으로 변환 가능한지 확인
    temp_text = temp_text.replace('(', '').replace(')', '').replace(',', '')
    try:
        float(temp_text)
        return True
    except ValueError:
        return False

def is_period_text(text):
    """
    텍스트가 '제 n기' 형태인지 판별합니다.
    """
    text = text.strip()
    return re.match(r'제\s*\S+\s*기', text) is not None

def is_date_format(text):
    """
    텍스트가 'NNNN-NN-NN' 형태인지 판별합니다.
    """
    text = text.strip()
    return re.match(r'^\d{4}-\d{2}-\d{2}$', text) is not None

def get_optimized_column_axes(ocr_items):
    """
    OCR 항목들의 최적의 열 축(axis)을 결정합니다.
    """
    if not ocr_items:
        return [], None
    
    left_coords = [item[0][0][0] for item in ocr_items]
    center_coords = [(item[0][0][0] + item[0][2][0]) / 2 for item in ocr_items]
    right_coords = [item[0][2][0] for item in ocr_items]
    
    candidate_axes = {
        'left': left_coords,
        'center': center_coords,
        'right': right_coords
    }
    
    best_variance = float('inf')
    best_axis = []
    best_alignment = None
    
    for alignment_type, coords in candidate_axes.items():
        coords.sort()
        clusters = []
        if coords:
            current_cluster = [coords[0]]
            for i in range(1, len(coords)):
                if coords[i] - current_cluster[-1] < 50:
                    current_cluster.append(coords[i])
                else:
                    clusters.append(current_cluster)
                    current_cluster = [coords[i]]
            if current_cluster:
                clusters.append(current_cluster)
        
        avg_variance = sum(np.var(c) for c in clusters if len(c) > 1) / len(clusters) if clusters else 0
        
        if avg_variance < best_variance:
            best_variance = avg_variance
            best_alignment = alignment_type
            best_axis = [np.mean(c) for c in clusters]

    return sorted(best_axis), best_alignment

def process_table_by_box_and_content(image_path, output_path):
    """
    OCR 결과를 박스 단위로 처리하여 표를 생성합니다.

    Args:
        image_path (str): 입력 이미지 파일 경로.
        output_path (str): 출력 CSV 파일 경로.
    """
    try:
        if not os.path.exists(image_path):
            print(f"오류: 이미지를 찾을 수 없습니다: {image_path}")
            return

        print(f"이미지 불러오는 중: {image_path}")
        img = cv2.imread(image_path)
        
        # 개선된 전처리 함수를 적용합니다.
        processed_img = preprocess_for_numbers(img)
        if processed_img is None:
            return
        
        reader = easyocr.Reader(['ko', 'en'])
        full_ocr_results = reader.readtext(processed_img)
        print("전체 OCR 결과 불러오기 완료.")
        
        if not full_ocr_results:
            print("이미지에서 텍스트를 찾을 수 없습니다. 종료합니다.")
            return

        processed_results = []
        for bbox, text, prob in full_ocr_results:
            stripped_text = text.strip().replace("'", "")
            
            # OCR 결과를 유형에 따라 적절하게 후처리합니다.
            if is_period_text(stripped_text) or is_date_format(stripped_text):
                processed_results.append((bbox, replace_words(stripped_text), prob))
            elif is_numeric_text(stripped_text):
                cleaned_text = clean_numeric_text(stripped_text)
                formatted_text = format_number_with_commas(cleaned_text)
                processed_results.append((bbox, formatted_text, prob))
            else:
                processed_results.append((bbox, replace_words(stripped_text), prob))

        # 항목들을 y좌표 순으로 정렬하여 행을 구성합니다.
        processed_results.sort(key=lambda x: x[0][0][1])
        avg_height = np.mean([bbox[2][1] - bbox[0][1] for (bbox, text, prob) in processed_results])

        rows = []
        if processed_results:
            current_row = [processed_results[0]]
            for i in range(1, len(processed_results)):
                y_diff = processed_results[i][0][0][1] - current_row[-1][0][0][1]
                if y_diff > avg_height * 0.7:
                    rows.append(current_row)
                    current_row = [processed_results[i]]
                else:
                    current_row.append(processed_results[i])
            rows.append(current_row)

        # 데이터 행의 숫자들만 모아 열 축을 계산합니다.
        numeric_items_in_data_rows = []
        if len(rows) > 0:
            for row in rows:
                for item in row:
                    text = item[1]
                    if is_numeric_text(text):
                        numeric_items_in_data_rows.append(item)

        data_axes, _ = get_optimized_column_axes(numeric_items_in_data_rows)
        all_column_axes = sorted(list(set(data_axes)))
        
        num_columns = len(all_column_axes)
        print(f"\n--- 단계 1: 데이터 행을 기준으로 최적의 열 축 계산 ---")
        print(f"최종 기준점 X좌표: {[int(p) for p in all_column_axes]}")

        final_table_data = []

        for r_idx, row in enumerate(rows):
            row.sort(key=lambda x: x[0][0][0])
            
            row_cells = [""] * (num_columns + 1)
            
            first_item_text = row[0][1].strip() if row else ""
            
            is_header_format = is_period_text(first_item_text) or is_date_format(first_item_text)
            
            if is_header_format:
                row_cells[0] = ""
                items_to_process = row
            else:
                row_cells[0] = first_item_text
                items_to_process = row[1:]
            
            for bbox, text, _ in items_to_process:
                parts = text.split()
                if len(parts) >= 2 and all(is_numeric_text(p) for p in parts):
                    if len(all_column_axes) >= len(parts):
                        x_coord = (bbox[0][0] + bbox[2][0]) / 2
                        dist = np.abs(np.array(all_column_axes) - x_coord)
                        closest_indices = np.argsort(dist)[:len(parts)]
                        sorted_indices = sorted(closest_indices)
                        
                        for i, part in enumerate(parts):
                            target_col_idx = sorted_indices[i] + 1
                            if target_col_idx < len(row_cells):
                                row_cells[target_col_idx] = format_number_with_commas(part)
                else:
                    x_coord = (bbox[0][0] + bbox[2][0]) / 2
                    if all_column_axes:
                        closest_col_idx = np.argmin(np.abs(np.array(all_column_axes) - x_coord))
                        target_col_idx = closest_col_idx + 1

                        if target_col_idx < len(row_cells) and row_cells[target_col_idx] == "":
                              row_cells[target_col_idx] = text
                        else:
                            is_added = False
                            for i in range(target_col_idx + 1, len(row_cells)):
                                if row_cells[i] == "":
                                    row_cells[i] = text
                                    is_added = True
                                    break
                            if not is_added:
                                row_cells[target_col_idx] = (row_cells[target_col_idx] + " " + text).strip()
                
            final_table_data.append(row_cells)
        
        print("\n--- 단계 2: 최종 결과를 CSV 파일에 기록 ---")
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerows(final_table_data)
        
        print(f"\n모든 결과가 '{output_path}' 파일에 저장되었습니다.")
        print("\n최종 결과 미리보기:")
        for row in final_table_data:
            print(row)

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")

if __name__ == "__main__":
    # 사용자 이미지 경로를 여기에 입력하세요.
    image_file_path = r"C:\Users\3CLASS_004\Documents\GitHub\3team\Python\Analyze\Asset\TestImg\image38.jpg"
    output_csv_path = r"C:\Users\3CLASS_004\Documents\GitHub\3team\Python\Analyze\Asset\Result\OCR_result.csv"
    process_table_by_box_and_content(image_file_path, output_csv_path)
