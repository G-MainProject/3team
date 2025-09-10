# Libs/revenue.py
from datetime import datetime
from .dart_client import get_corp_code, get_year_report_revenue

def _sub(a, b):
    if a is None or b is None:
        return None
    return a - b

def derive_quarters_from_reports(reports: dict):
    """
    reports: {"Q1":{"amount","add"}, "H1":{"amount","add"}, "Q3":{"amount","add"}, "FY":{"amount","add"}}
    누적(add)로 분기금액 복원:
      Q1 = Q1.add
      Q2 = H1.add - Q1.add
      Q3 = Q3.add - H1.add
      Q4 = FY.add - Q3.add
    누적이 없으면 amount 일부 fallback.
    """
    q1_add = (reports.get("Q1") or {}).get("add")
    h1_add = (reports.get("H1") or {}).get("add")
    q3_add = (reports.get("Q3") or {}).get("add")
    fy_add = (reports.get("FY") or {}).get("add")

    q = {
        "Q1": q1_add,
        "Q2": _sub(h1_add, q1_add),
        "Q3": _sub(q3_add, h1_add),
        "Q4": _sub(fy_add, q3_add),
    }
    # Q4 보강: FY.add가 없고 FY.amount가 있는 경우 Q4 = FY.amount - Q3.add
    if q["Q4"] is None:
        fy_amount = (reports.get("FY") or {}).get("amount")
        if fy_amount is not None and q3_add is not None:
            q["Q4"] = _sub(fy_amount, q3_add)
    # 누적이 전혀 없는 경우 최소한 Q1.amount라도 대입
    if q["Q1"] is None and (reports.get("Q1") or {}).get("amount") is not None:
        q["Q1"] = (reports["Q1"]["amount"])
    return q

def collect_recent_years(project_root: str, stock_code: str, years: int = 5, fs_div="CFS"):
    """
    종목코드를 받아 최근 N년 분기 매출액을 수집해 구조화해 반환
    return:
    {
      "stock_code": "...",
      "corp_code": "...",
      "fs_div": "CFS",
      "collected_years": [2023, 2024, 2025],
      "data": [
        {"year": 2023, "reports": {...}, "quarters": {"Q1":..., "Q2":..., "Q3":..., "Q4":...}},
        ...
      ]
    }
    """
    corp_code = get_corp_code(project_root, stock_code)
    if not corp_code:
        raise ValueError(f"종목코드 {stock_code} 를 DART 고유번호로 변환하지 못했습니다.")

    this_year = datetime.now().year
    ys = list(range(this_year - years + 1, this_year + 1))

    out = {
        "stock_code": stock_code,
        "corp_code": corp_code,
        "fs_div": fs_div,
        "collected_years": ys,
        "data": []
    }

    for y in ys:
        reports = get_year_report_revenue(corp_code, y, fs_div=fs_div)
        quarters = derive_quarters_from_reports(reports)
        out["data"].append({"year": y, "reports": reports, "quarters": quarters})
    return out
