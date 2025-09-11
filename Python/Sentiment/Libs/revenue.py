# Libs/revenue.py
from datetime import datetime
from .dart_client import (
    get_corp_code,
    get_year_report_revenue,
    get_year_report_operating_profit,
    get_year_report_net_profit,
    get_year_report_balance_snapshots,
)

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

def collect_recent_years(project_root: str, stock_code: str, years: int = 8, fs_div="CFS"):
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

def _safe_div(a, b):
    try:
        if a is None or b in (None, 0):
            return None
        return a / b
    except Exception:
        return None

def ratios_quarters_from_snapshots(reports: dict):
    """
    Convert balance snapshots {Q1,H1,Q3,FY} into quarter-labeled ratios dict.
    Mapping: Q1->Q1, Q2<-H1, Q3->Q3, Q4->FY
    returns {Q1: {debt_ratio, current_ratio}, ...}
    """
    def get_ratio(key):
        r = (reports.get(key) or {})
        return {
            "debt_ratio": r.get("debt_ratio"),
            "current_ratio": r.get("current_ratio"),
        }

    return {
        "Q1": get_ratio("Q1"),
        "Q2": get_ratio("H1"),
        "Q3": get_ratio("Q3"),
        "Q4": get_ratio("FY"),
    }

def collect_recent_financials(project_root: str, stock_code: str, years: int = 8, fs_div="CFS"):
    """
    확장 수집: 매출액/영업이익/당기순이익(분기금액 복원) + 부채비율/유동비율(스냅샷 기반)을 함께 반환.
    return:
    {
      stock_code, corp_code, fs_div, collected_years,
      data: [
        {
          year,
          revenue:   {reports:{Q1/H1/Q3/FY:{amount,add}}, quarters:{Q1~Q4:int|None}},
          op_profit: {reports:{...}, quarters:{...}},
          net_profit:{reports:{...}, quarters:{...}},
          ratios:    {reports:{Q1/H1/Q3/FY:{liabilities,equity,current_assets,current_liabilities,debt_ratio,current_ratio}},
                      quarters:{Q1~Q4:{debt_ratio,current_ratio}}},
        }, ...
      ]
    }
    """
    corp_code = get_corp_code(project_root, stock_code)
    if not corp_code:
        raise ValueError(f"종목코드 {stock_code} 의 DART 고유번호를 변환하지 못했습니다")

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
        rev_reports = get_year_report_revenue(corp_code, y, fs_div=fs_div)
        op_reports  = get_year_report_operating_profit(corp_code, y, fs_div=fs_div)
        net_reports = get_year_report_net_profit(corp_code, y, fs_div=fs_div)
        bal_reports = get_year_report_balance_snapshots(corp_code, y, fs_div=fs_div)

        item = {
            "year": y,
            "revenue": {
                "reports": rev_reports,
                "quarters": derive_quarters_from_reports(rev_reports),
            },
            "op_profit": {
                "reports": op_reports,
                "quarters": derive_quarters_from_reports(op_reports),
            },
            "net_profit": {
                "reports": net_reports,
                "quarters": derive_quarters_from_reports(net_reports),
            },
            "ratios": {
                "reports": bal_reports,
                "quarters": ratios_quarters_from_snapshots(bal_reports),
            },
        }
        out["data"].append(item)

    return out
