# -*- coding: utf-8 -*-
import os, re, csv, gc, sys, time
import cv2
import numpy as np
import easyocr
from OCR_D import replace_words

# ===== CPU 안전 옵션: 스레드 최소화 =====
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
try:
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
except Exception:
    pass
try:
    cv2.setNumThreads(1)
except Exception:
    pass


# ===================== 텍스트 정규화 =====================
def clean_numeric_text(text):
    return re.sub(r'[^0-9.\-()]+', '', str(text).replace(',', ''))

def format_number_with_commas(text):
    t = str(text).strip()
    if t.upper() in ["NA", "N/A", "-"]:
        return t
    cleaned = t.replace(',', '')
    try:
        number = float(cleaned.replace('-', '').replace('(', '').replace(')', ''))
        formatted = f"{int(number):,}" if number.is_integer() else f"{number:,}"
        if '-' in t or '(' in t:
            return f"-{formatted}"
        return formatted
    except ValueError:
        return t

def is_numeric_text(text):
    t = str(text).strip()
    if re.search(r'[가-힣]', t):
        return False
    if t.upper() in ["NA", "N/A", "-"]:
        return True
    temp = re.sub(r'[^0-9.\-(),]+', '', t)
    if not temp:
        return False
    temp = temp.replace('(', '').replace(')', '').replace(',', '')
    try:
        float(temp); return True
    except ValueError:
        return False

def is_period_text(text):
    return re.match(r'제\s*\S+\s*기', str(text).strip()) is not None

def is_date_format(text):
    return re.match(r'^\d{4}-\d{2,3}(?:~\s*\d{4}-\d{2,3})?$', str(text).strip()) is not None


# ===================== 전처리 (k-means 제거, HSV 마스크) =====================
def preprocess_image(img):
    """
    다운스케일 없이 HSV 기반으로 검정/빨강 텍스트를 강조한 흑백 이미지를 생성.
    - k-means 제거로 CPU 사용량 크게 감소
    - 해상도 유지
    """
    if img is None:
        print("오류: 유효하지 않은 이미지", flush=True)
        return None

    # 배경 약화
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, bgmask = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
    bg_suppressed = cv2.bitwise_and(img, img, mask=bgmask)

    # HSV 변환
    hsv = cv2.cvtColor(bg_suppressed, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    # 검정 텍스트(어두움) + 빨강 텍스트(고채도 빨강) 마스크
    # 값 범위는 이미지마다 다르니 여유 범위로 잡음
    mask_black = (v < 90).astype(np.uint8) * 255
    mask_red1 = ((h <= 12) & (s >= 90) & (v >= 60)).astype(np.uint8) * 255
    mask_red2 = ((h >= 170) & (s >= 90) & (v >= 60)).astype(np.uint8) * 255
    text_mask = cv2.bitwise_or(mask_black, cv2.bitwise_or(mask_red1, mask_red2))

    # 약간의 팽창으로 끊김 완화
    kernel = np.ones((2, 2), np.uint8)
    text_mask = cv2.dilate(text_mask, kernel, iterations=1)

    # OCR 친화적으로 흑백 반전
    bw = cv2.bitwise_not(text_mask)
    return bw


# ===================== 축 자동 추정 =====================
def infer_axes_auto(rows, img_width):
    if not rows:
        return []
    primary_th = max(60.0, img_width * 0.035)
    header_points, data_points = [], []

    first_row = rows[0]
    for bbox, text, _ in first_row:
        if is_numeric_text(text) or is_date_format(text):
            x_mid = (bbox[0][0] + bbox[2][0]) / 2
            header_points.append((x_mid, -1))

    for r_idx, row in enumerate(rows):
        for bbox, text, _ in row:
            if is_numeric_text(text) or str(text).strip().upper() in ["NA", "N/A", "-"]:
                x_mid = (bbox[0][0] + bbox[2][0]) / 2
                data_points.append((x_mid, r_idx))

    points = header_points + data_points
    if not points:
        return []

    if header_points and data_points:
        h_mean = np.mean([x for x, _ in header_points])
        d_mean = np.mean([x for x, _ in data_points])
        shift = h_mean - d_mean
        if abs(shift) > 20:
            data_points = [(x + shift / 2.0, r) for x, r in data_points]
    points = sorted(header_points + data_points, key=lambda p: p[0])

    clusters = []
    cur = [points[0]]
    for x, ri in points[1:]:
        if abs(x - cur[-1][0]) <= primary_th:
            cur.append((x, ri))
        else:
            clusters.append(cur); cur = [(x, ri)]
    clusters.append(cur)

    min_rows_required = max(2, int(np.ceil(0.12 * max(1, len(rows)))))
    axes = []
    for cl in clusters:
        rows_in = set(ri for _, ri in cl)
        has_header = (-1 in rows_in)
        if has_header or len([r for r in rows_in if r >= 0]) >= min_rows_required:
            axes.append(float(np.mean([x for x, _ in cl])))

    if len(axes) < max(2, len(header_points)):
        axes = sorted([x for x, _ in header_points])
    return sorted(axes)


# ===================== 헤더 정규화 =====================
def _normalize_header_cell(raw):
    if raw is None:
        return ''
    s = str(raw).strip()
    est = False
    if s.startswith('-'):
        est = True
        s = s[1:].lstrip()
    digits = re.findall(r'\d', s)
    if len(digits) >= 6:
        year, month = ''.join(digits[:4]), ''.join(digits[4:6])
        header = f"{year}-{month}"
        return header + "(E)" if est else header
    m = re.search(r'(\d{4})\D*?(\d{2})', s)
    if m:
        header = f"{m.group(1)}-{m.group(2)}"
        return header + "(E)" if est else header
    return s


# ===================== 후처리 규칙 =====================
def apply_custom_rules(table):
    if not table or not isinstance(table, list):
        return table

    out = [list(r) for r in table]

    # 1) 첫 셀 라벨 고정
    if len(out) >= 1 and len(out[0]) >= 1:
        out[0][0] = '주요재무정보'

    # 2) 헤더 정규화 (삭제는 안 함)
    if len(out) >= 1 and len(out[0]) >= 2:
        for c in range(1, len(out[0])):
            out[0][c] = _normalize_header_cell(out[0][c])

    # 3) 라벨 칸 공백 제거
    for r in range(len(out)):
        if len(out[r]) >= 1 and isinstance(out[r][0], str):
            out[r][0] = re.sub(r'\s+', '', out[r][0])

    # 4) 쓰레기 행 제거(라벨도 비고 데이터도 거의 없으면 제거)
    cleaned = [out[0]]
    for r in range(1, len(out)):
        row = out[r]
        label = (row[0].strip() if len(row) > 0 else "")
        non_empty = sum(1 for x in row[1:] if str(x).strip() != "")
        if label == "" and non_empty <= 1:
            continue
        cleaned.append(row)
    out = cleaned

    # 5) 2행 삭제(더미 라인 제거) — 필요 없으면 주석 처리
    if len(out) > 1:
        del out[1]

    # 6) 라벨 끝에 붙은 대형 숫자 분리 (예: '발행주식수(보통주)111251760')
    for r in range(1, len(out)):
        row = out[r]
        if not row:
            continue
        label = str(row[0]).strip()
        m = re.match(r'^([^\d]+?)(\d{5,})$', label)
        if not m:
            continue

        pure_label, trailing_num = m.group(1).strip(), m.group(2).strip()

        def _clean_num(s):
            return re.sub(r'[^0-9\-\.]', '', str(s))

        first_num_clean = None
        for c in range(1, len(row)):
            if str(row[c]).strip() != "":
                fc = _clean_num(row[c])
                if fc != "":
                    first_num_clean = fc
                    break

        trailing_clean = _clean_num(trailing_num)

        # (a) 이미 첫 숫자 셀과 동일하면 라벨만 정리
        if first_num_clean and trailing_clean == first_num_clean:
            row[0] = pure_label
            continue

        # (b) 비어있는 첫 숫자 열에 넣고, 없으면 col1에 배치
        insert_idx = None
        for c in range(1, len(row)):
            if str(row[c]).strip() == "":
                insert_idx = c
                break
        if insert_idx is None:
            insert_idx = 1

        try:
            as_int = int(trailing_clean)
            row[insert_idx] = f"{as_int:,}"
        except Exception:
            row[insert_idx] = format_number_with_commas(trailing_clean)

        row[0] = pure_label

    return out


# ===================== 단일 이미지 처리 =====================
def process_table_by_box_and_content(image_path, output_path, reader):
    try:
        img = cv2.imread(image_path)
        if img is None:
            print(f"[{os.path.basename(image_path)}] 이미지 로드 실패", flush=True)
            return
        img_w = img.shape[1]
        proc = preprocess_image(img)
        if proc is None:
            print(f"[{os.path.basename(image_path)}] 전처리 실패", flush=True)
            return

        # CPU 모드, 작은 배치로 천천히
        ocr = reader.readtext(proc, detail=1, paragraph=False, batch_size=1, decoder='greedy')
        if not ocr:
            print(f"[{os.path.basename(image_path)}] 텍스트 없음", flush=True)
            return

        processed = []
        for bbox, text, prob in ocr:
            t = str(text).strip().replace("'", "")
            if is_period_text(t) or is_date_format(t):
                processed.append((bbox, replace_words(t), prob))
            elif is_numeric_text(t):
                if t.upper() in ["NA", "N/A", "-"]:
                    processed.append((bbox, t.upper(), prob))
                else:
                    processed.append((bbox, clean_numeric_text(t), prob))
            else:
                processed.append((bbox, replace_words(t), prob))

        processed.sort(key=lambda x: x[0][0][1])
        avg_h = np.mean([b[2][1] - b[0][1] for b, _, _ in processed])
        rows, cur = [], [processed[0]]
        for i in range(1, len(processed)):
            if processed[i][0][0][1] - cur[-1][0][0][1] > avg_h * 0.7:
                rows.append(cur); cur = [processed[i]]
            else:
                cur.append(processed[i])
        rows.append(cur)

        axes = infer_axes_auto(rows, img_w)
        print(f"[{os.path.basename(image_path)}] 축 개수: {len(axes)}, 축: {[int(a) for a in axes]}", flush=True)

        final = []
        MIN_AXIS_MARGIN = 60
        min_axis = min(axes) if axes else None

        for row in rows:
            row.sort(key=lambda x: x[0][0][0])
            only_dates = all(is_date_format(i[1]) or is_period_text(i[1]) for i in row)
            if only_dates and len(row) >= 2:
                merged = ['']
                i = 0
                while i < len(row):
                    curi = row[i]
                    if i + 1 < len(row) and (row[i+1][0][0][0] - curi[0][2][0]) < 50:
                        merged.append(f"{curi[1].strip()} ~ {row[i+1][1].strip()}")
                        i += 2
                    else:
                        merged.append(curi[1].strip()); i += 1
                final.append(merged); continue

            label_items, data_items = [], []
            for bbox, text, _ in row:
                x_mid = (bbox[0][0] + bbox[2][0]) / 2
                not_numeric = not (is_numeric_text(text) or is_period_text(text) or is_date_format(text))
                left_of_axes = (min_axis is not None) and (x_mid < (min_axis - MIN_AXIS_MARGIN))
                if not_numeric or left_of_axes:
                    label_items.append((bbox, text))
                else:
                    data_items.append((bbox, text))

            label_items.sort(key=lambda x: x[0][0][0])
            label_text = " ".join([t.strip() for _, t in label_items]).strip()
            if not label_text and row:
                leftmost = min(row, key=lambda x: x[0][0][0])
                if not (is_numeric_text(leftmost[1]) or is_period_text(leftmost[1]) or is_date_format(leftmost[1])):
                    label_text = leftmost[1].strip()

            cells = [[] for _ in range(max(1, len(axes)) + 1)]
            cells[0].append(label_text)
            for bbox, text in data_items:
                x_mid = (bbox[0][0] + bbox[2][0]) / 2
                col = int(np.argmin(np.abs(np.array(axes) - x_mid))) + 1 if len(axes) > 0 else 1
                col = min(col, len(cells) - 1)
                cells[col].append(str(text))

            row_out = []
            for i, c in enumerate(cells):
                val = "".join(c).strip()
                if i > 0 and is_numeric_text(val):
                    row_out.append(format_number_with_commas(val))
                else:
                    row_out.append(val)
            final.append(row_out)

        final = apply_custom_rules(final)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerows(final)

        print(f"✅ 저장완료: {output_path} (총 {len(final)}행)", flush=True)
    except Exception as e:
        print(f"[{os.path.basename(image_path)}] 오류 발생: {e}", flush=True)
    finally:
        del img
        if 'proc' in locals():
            del proc
        gc.collect()


# ===================== 배치 =====================
def process_folder_images(input_dir, output_dir, exts=None, gpu=False, pause_sec=1.5):
    if exts is None:
        exts = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tif', '.tiff'}

    if not os.path.isdir(input_dir):
        print(f"입력 폴더가 없습니다: {input_dir}", flush=True)
        return

    os.makedirs(output_dir, exist_ok=True)

    print("EasyOCR 초기화 중... (CPU 모드)", flush=True)
    reader = easyocr.Reader(['ko', 'en'], gpu=gpu, verbose=True)

    files = sorted([f for f in os.listdir(input_dir) if os.path.splitext(f)[1].lower() in exts])
    if not files:
        print("처리할 이미지가 없습니다.", flush=True)
        return

    print(f"총 {len(files)}개 이미지 처리 시작", flush=True)
    processed_cnt, failed_cnt = 0, 0
    for idx, fname in enumerate(files, 1):
        in_path = os.path.join(input_dir, fname)
        base, _ = os.path.splitext(fname)
        out_path = os.path.join(output_dir, f"{base}.csv")
        print(f"\n[{idx}/{len(files)}] 처리: {fname}", flush=True)
        try:
            process_table_by_box_and_content(in_path, out_path, reader=reader)
            processed_cnt += 1
        except Exception as e:
            print(f"처리 실패: {fname} -> {e}", flush=True)
            failed_cnt += 1

        # CPU 여유를 위해 잠깐 쉬기
        time.sleep(pause_sec)

    print(f"\n=== 완료 ===\n성공: {processed_cnt}  실패: {failed_cnt}  총: {len(files)}", flush=True)


# ===================== 실행 =====================
if __name__ == "__main__":
    input_dir = r"C:\Users\39200\OneDrive\문서\GitHub\3team\Python\Analyze\Asset\Img"
    output_dir = r"C:\Users\39200\OneDrive\문서\GitHub\3team\Python\Analyze\Asset\Result"
    process_folder_images(input_dir, output_dir, gpu=False, pause_sec=5.0)
