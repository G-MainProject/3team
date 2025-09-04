# -*- coding: utf-8 -*-
from pathlib import Path
import csv
import re

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
SYMBOLS_CSV = DATA_DIR / "symbols_krx.csv"

# 후보 컬럼명
NAME_COLS = [
    "한글 종목약명","한글종목약명",
    "한글 종목명","한글종목명",
    "회사명","종목명","종목 이름","종목명(한글)"
]
CODE_COLS = ["단축코드","단축 코드","종목코드","종목 코드","code","CODE"]

def _norm_name(s: str) -> str:
    if not isinstance(s, str): return ""
    s = s.strip()
    s = re.sub(r"^\((주|株)\)\s*", "", s)   # (주) 제거
    s = s.replace("주식회사 ", "")
    return s

def _read_rows():
    """
    symbols_krx.csv를 읽어 행 이터레이터를 반환.
    - 구분자: 콤마/탭 자동 시도
    - 인코딩: utf-8-sig → cp949 순서로 시도
    """
    if not SYMBOLS_CSV.exists():
        raise FileNotFoundError(f"심볼 파일이 없습니다: {SYMBOLS_CSV}")
    encodings = ["utf-8-sig", "cp949"]
    seps = [",", "\t"]
    last_err = None
    for enc in encodings:
        for sep in seps:
            try:
                with SYMBOLS_CSV.open("r", encoding=enc, newline="") as f:
                    reader = csv.DictReader(f, delimiter=sep)
                    # 헤더가 비정상이면 건너뜀
                    if not reader.fieldnames or len(reader.fieldnames) < 2:
                        continue
                    for row in reader:
                        yield row
                return
            except Exception as e:
                last_err = e
                continue
    if last_err:
        raise last_err

def _pick_col(row_keys, candidates):
    for cand in candidates:
        for k in row_keys:
            if k.strip().replace(" ", "") == cand.replace(" ", ""):
                return k
    return None

def load_symbol_map() -> dict[str, str]:
    """
    CSV → {종목명: 6자리코드} 매핑 딕셔너리 생성
    - 이름: '한글 종목약명' 우선, 없으면 '한글 종목명/회사명/종목명' 등 사용
    - 코드: '단축코드/종목코드/code' 중 하나
    """
    m: dict[str, str] = {}
    # 첫 줄을 한 번 읽어 컬럼명 매핑을 정한다
    gen = _read_rows()
    try:
        first = next(gen)
    except StopIteration:
        return m

    name_key = _pick_col(first.keys(), NAME_COLS)
    code_key = _pick_col(first.keys(), CODE_COLS)
    if not name_key or not code_key:
        raise RuntimeError(
            f"CSV 컬럼을 찾지 못했습니다. 이름 후보={NAME_COLS}, 코드 후보={CODE_COLS}"
        )

    def add_row(row):
        name = _norm_name(row.get(name_key, ""))
        code = (row.get(code_key, "") or "").strip()
        code = re.sub(r"\D", "", code)  # 숫자만
        if code:
            code = code.zfill(6)        # 6자리 zero-pad
        if name and len(code) == 6 and code.isdigit():
            m[name] = code

    add_row(first)
    for row in gen:
        add_row(row)

    return m

def resolve_code_by_name(name: str, m: dict[str, str]) -> tuple[str | None, list[tuple[str, str]]]:
    """
    정확 일치 → 코드 반환.
    없으면 부분일치 후보 최대 10개 반환.
    """
    q = _norm_name(name)
    if q in m:
        return m[q], []
    ql = q.lower()
    cands = [(n, c) for n, c in m.items() if ql in n.lower()]
    if len(cands) == 1:
        return cands[0][1], []
    return None, cands[:10]
