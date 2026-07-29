import json
import math
import re
from datetime import date
from pathlib import Path

import pandas as pd

from report_metrics import (
    MetricRegistry,
    format_count,
    format_money,
    format_percent,
    ratio,
    yoy_rate,
)


BASE_DIR = Path(__file__).resolve().parent
WORKBOOK = BASE_DIR.parent / "Branch Report.xlsx"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


MONTH_ORDER = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
TOTAL_LABELS = {"grand total", "total", "2025 total", "2026 total"}


def clean_name(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def is_total_label(value):
    return clean_name(value).lower() in TOTAL_LABELS or clean_name(value).lower().endswith(" total")


def parse_number(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = str(value).strip()
    if text in {"", "-", "—", "nan"}:
        return None
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    text = text.replace("EGP", "").replace(",", "").replace("%", "").strip()
    text = text.replace("(", "-").replace(")", "")
    try:
        number = float(text)
    except ValueError:
        return None
    if negative and number > 0:
        number *= -1
    return number


def parse_percent(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = str(value).strip()
    num = parse_number(text)
    if num is None:
        return None
    return num / 100 if "%" in text else num


def safe_div(numerator, denominator):
    result = ratio(numerator, denominator)
    return float(result) if result is not None else None


def safe_yoy(current, previous):
    result = yoy_rate(current, previous)
    return float(result) if result is not None else None


def money(value):
    return 0 if value is None else float(value)


def nearly_equal(actual, expected, tolerance=1):
    return abs(money(actual) - money(expected)) <= tolerance


def classify_yoy(previous, current):
    previous_value = money(previous)
    current_value = money(current)
    if previous_value == 0 and current_value > 0:
        return "New Base"
    if previous_value > 0 and current_value == 0:
        return "No Current Production"
    if previous_value == 0 and current_value == 0:
        return "No Production"
    if current_value > previous_value:
        return "Positive Growth"
    if current_value < previous_value:
        return "Negative Growth"
    return "Flat"


def month_sort_key(month):
    return MONTH_ORDER.index(month) if month in MONTH_ORDER else len(MONTH_ORDER)


def month_range_label(months, year=2026):
    available = [m for m in MONTH_ORDER if m in months]
    if not available:
        return f"YTD {year}"
    return f"{available[0]}-{available[-1]} {year}"


def find_row(df, text, start=0, col=None):
    target = text.lower()
    for ridx in range(start, len(df)):
        values = [df.iat[ridx, col]] if col is not None else df.iloc[ridx].tolist()
        if any(target == clean_name(value).lower() for value in values):
            return ridx
    return None


def normalize_header(value):
    return re.sub(r"[^a-z0-9]+", " ", clean_name(value).lower()).strip()


def extract_summary_rows(df, section_titles, field_aliases, percent_fields=None):
    percent_fields = set(percent_fields or [])
    section_row = None
    for title in section_titles:
        section_row = find_row(df, title, col=2)
        if section_row is not None:
            break
    if section_row is None:
        raise ValueError(f"Missing workbook section: {section_titles[0]}")

    header_row = find_row(df, "Month", start=section_row, col=2)
    if header_row is None:
        raise ValueError(f"Missing Month header after workbook section: {section_titles[0]}")

    headers = {
        normalize_header(df.iat[header_row, cidx]): cidx
        for cidx in range(df.shape[1])
        if normalize_header(df.iat[header_row, cidx])
    }
    columns = {}
    for key, aliases in field_aliases.items():
        columns[key] = next((headers[normalize_header(alias)] for alias in aliases if normalize_header(alias) in headers), None)
        if columns[key] is None:
            raise ValueError(f"Missing column '{aliases[0]}' in workbook section: {section_titles[0]}")

    records = []
    total = None
    for ridx in range(header_row + 1, len(df)):
        month = clean_name(df.iat[ridx, columns["month"]])
        if month not in MONTH_ORDER and month != "Grand Total":
            if records:
                break
            continue
        record = {"month": month}
        for key, cidx in columns.items():
            if key == "month":
                continue
            parser = parse_percent if key in percent_fields else parse_number
            record[key] = parser(df.iat[ridx, cidx])
        if month == "Grand Total":
            total = record
            break
        records.append(record)
    if total is None:
        raise ValueError(f"Missing Grand Total row in workbook section: {section_titles[0]}")
    return records, total


def row_to_record(row, cols, name_key):
    record = {name_key: clean_name(row.iloc[cols[0]])}
    record.update(
        {
            "premium_2025": parse_number(row.iloc[cols[1]]),
            "premium_2026": parse_number(row.iloc[cols[2]]),
            "source_yoy_change": parse_number(row.iloc[cols[3]]),
            "source_yoy_change_pct": parse_percent(row.iloc[cols[4]]),
            "pending_operation_paid": parse_number(row.iloc[cols[5]]),
            "pending_finance": parse_number(row.iloc[cols[6]]),
            "pending_payment": parse_number(row.iloc[cols[7]]),
            "new_premium": parse_number(row.iloc[cols[8]]),
            "renewal_premium": parse_number(row.iloc[cols[9]]),
            "approved_policies": parse_number(row.iloc[cols[10]]),
            "total_policies": parse_number(row.iloc[cols[11]]),
            "total_policies_ly": parse_number(row.iloc[cols[12]]),
            "new_policies": parse_number(row.iloc[cols[13]]),
            "renewal_policies": parse_number(row.iloc[cols[14]]),
            "retail_approved_gross": parse_number(row.iloc[cols[15]]),
            "corporate_approved_gross": parse_number(row.iloc[cols[16]]),
            "motor_premium": parse_number(row.iloc[cols[17]]),
            "non_motor_premium": parse_number(row.iloc[cols[18]]),
        }
    )
    record["yoy_change"] = (
        record["premium_2026"] - record["premium_2025"]
        if record["premium_2026"] is not None and record["premium_2025"] is not None
        else None
    )
    record["yoy_change_pct"] = safe_yoy(record["premium_2026"], record["premium_2025"])
    record["contribution_pct"] = None
    record["avg_premium_per_policy"] = safe_div(record["premium_2026"], record["approved_policies"])
    record["renewal_mix_pct"] = safe_div(record["renewal_premium"], record["premium_2026"])
    record["motor_mix_pct"] = safe_div(record["motor_premium"], record["premium_2026"])
    record["pending_total"] = sum(money(record[k]) for k in ["pending_operation_paid", "pending_finance", "pending_payment"])
    record["growth_class"] = classify_yoy(record["premium_2025"], record["premium_2026"])
    return record


def extract_entity_table(df, start_row, end_row, name_key):
    cols = list(range(2, 21))
    records = []
    total = None
    for ridx in range(start_row, end_row + 1):
        row = df.iloc[ridx]
        name = clean_name(row.iloc[2])
        if not name:
            continue
        rec = row_to_record(row, cols, name_key)
        if name.lower() == "grand total":
            total = rec
        elif not is_total_label(name):
            records.append(rec)
    total_2026 = total["premium_2026"] if total else sum(money(r["premium_2026"]) for r in records)
    for rec in records:
        rec["contribution_pct"] = safe_div(rec["premium_2026"], total_2026)
    return records, total


def extract_sellers(df):
    title_row = find_row(df, "TOP 20 Sellers", col=2)
    if title_row is None:
        return [], None
    header_row = find_row(df, "Branch", start=title_row + 1, col=2)
    if header_row is None:
        return [], None
    cols = list(range(2, 21))
    records = []
    total = None
    for ridx in range(header_row + 1, len(df)):
        row = df.iloc[ridx]
        name = clean_name(row.iloc[2])
        if not name:
            if records:
                break
            continue
        rec = row_to_record(row, cols, "seller")
        if name.lower() == "grand total":
            total = rec
            break
        if not is_total_label(name):
            records.append(rec)
    total_2026 = total["premium_2026"] if total else sum(money(r["premium_2026"]) for r in records)
    for rec in records:
        rec["contribution_pct"] = safe_div(rec["premium_2026"], total_2026)
    return records, total


def extract_branch_breakdown(df):
    cols = list(range(2, 21))
    records = []
    monthly = []
    grand_total = None
    current_branch = None
    header_row = find_row(df, "Branch", col=2) or 17
    sellers_row = find_row(df, "TOP 20 Sellers", start=header_row + 1, col=2) or len(df)
    for ridx in range(header_row + 1, sellers_row):
        row = df.iloc[ridx]
        label = clean_name(row.iloc[2])
        if not label:
            continue
        if label in MONTH_ORDER and current_branch:
            rec = row_to_record(row, cols, "month")
            rec["branch"] = current_branch
            monthly.append(rec)
            continue
        if label == "Grand Total":
            grand_total = row_to_record(row, cols, "branch")
            break
        if label.endswith(" Total"):
            branch_name = label[:-6]
            rec = row_to_record(row, cols, "branch")
            rec["branch"] = branch_name
            records.append(rec)
            current_branch = None
            continue
        current_branch = label
    total_2026 = grand_total["premium_2026"] if grand_total else sum(money(r["premium_2026"]) for r in records)
    for rec in records:
        rec["contribution_pct"] = safe_div(rec["premium_2026"], total_2026)
    return records, grand_total, monthly


def extract_branches_per_month(df):
    header_row = find_row(df, "Branch", start=560, col=2)
    if header_row is None:
        return []
    month_cols = [(clean_name(df.iat[header_row, c]), c) for c in range(3, min(df.shape[1], 11))]
    month_cols = [(m, c) for m, c in month_cols if m in MONTH_ORDER]
    records = []
    for ridx in range(header_row + 1, len(df)):
        branch = clean_name(df.iat[ridx, 2])
        if not branch:
            continue
        if branch == "Grand Total":
            break
        for month, col in month_cols:
            records.append({"branch": branch, "month": month, "premium_2026": parse_number(df.iat[ridx, col])})
    return records


def extract_kpis(df):
    kpis = {}
    for ridx in range(12, 20):
        name = clean_name(df.iat[ridx, 2])
        if not name:
            continue
        value_2025 = parse_number(df.iat[ridx, 3])
        value_2026 = parse_number(df.iat[ridx, 4])
        kpis[name] = {
            "label": name,
            "value_2025": value_2025,
            "value_2026": value_2026,
            "change": value_2026 - value_2025 if value_2026 is not None and value_2025 is not None else None,
            "change_pct": safe_yoy(value_2026, value_2025),
            "source_change": parse_number(df.iat[ridx, 5]),
            "source_change_pct": parse_percent(df.iat[ridx, 6]),
        }
    return kpis


def extract_renewals(df):
    records = []
    for ridx in range(13, 21):
        month = clean_name(df.iat[ridx, 9])
        if month not in MONTH_ORDER and month != "Grand Total":
            continue
        renewed = parse_number(df.iat[ridx, 10])
        up_for_renewal = parse_number(df.iat[ridx, 11])
        not_renewed = None if renewed is None or up_for_renewal is None else up_for_renewal - renewed
        rate = safe_div(renewed, up_for_renewal)
        records.append(
            {
                "month": month,
                "renewed_policies": renewed,
                "policies_up_for_renewal": up_for_renewal,
                "not_renewed_policies": not_renewed,
                "renewal_rate": rate,
            }
        )
    return records


def extract_monthly(df):
    fields = {
        "month": ["Month"],
        "new_premium_2025": ["New Premiums 2025"],
        "renewal_premium_2025": ["Renewal Premiums 2025"],
        "other_premium_2025": ["Other Policies (Endorsement + Collection ) 2025"],
        "new_premium": ["New Premiums 2026"],
        "renewal_premium": ["Renewal Premiums 2026", "Renewal Premuims 2026"],
        "endorsement_premium": ["Other Policies (Endorsement + Collection ) 2026"],
        "actual_2025": ["2025"],
        "actual_2026": ["2026"],
        "target_2026": ["Target ( 2025 + 25%)"],
        "target_achievement_pct": ["Target Achievement %"],
        "yoy_change": ["2025 VS 2026 YOY"],
        "motor_premium": ["Motor Premiums 2026"],
        "non_motor_premium": ["Non-Motor Premiums 2026"],
        "motor_premium_2025": ["Motor Premium 2025", "Motor Premiums 2025"],
        "non_motor_premium_2025": ["Non-Motor Premium 2025", "Non-Motor Premiums 2025"],
        "pending_finance": ["Pending Finance"],
    }
    records, total = extract_summary_rows(
        df,
        ["2025 vs 2026 By Premium Amount Summary", "2025 vs 2026 By Summary"],
        fields,
        percent_fields={"target_achievement_pct"},
    )
    for record in [*records, total]:
        record["source_target_achievement_pct"] = record["target_achievement_pct"]
        record["source_yoy_change"] = record["yoy_change"]
        record["yoy_change"] = (
            record["actual_2026"] - record["actual_2025"]
            if record["actual_2026"] is not None and record["actual_2025"] is not None
            else None
        )
        record["target_achievement_pct"] = safe_div(record["actual_2026"], record["target_2026"])
        record["yoy_pct"] = safe_yoy(record["actual_2026"], record["actual_2025"])
    return records, total


def extract_monthly_counts(df):
    fields = {
        "month": ["Month"],
        "new_policies_2025": ["New Policies 2025"],
        "renewal_policies_2025": ["Renewal Policies 2025"],
        "other_policies_2025": ["Other Policies 2025"],
        "new_policies_2026": ["New Policies 2026"],
        "renewal_policies_2026": ["Renewal Policies 2026"],
        "other_policies_2026": ["Other Policies 2026"],
        "total_policies_2025": ["2025"],
        "total_policies_2026": ["2026"],
        "yoy_change": ["YoY"],
        "motor_policies_2026": ["Motor Policies 2026"],
        "non_motor_policies_2026": ["Non-Motor Policies 2026"],
        "motor_policies_2025": ["Motor Policies 2025"],
        "non_motor_policies_2025": ["Non-Motor Policies LY", "Non-Motor Policies 2025"],
        "motor_average_rate_2026": ["Motor Average Rate 2026"],
        "motor_average_rate_2025": ["Motor Average Rate 2025"],
    }
    return extract_summary_rows(
        df,
        ["2025 vs 2026 By Premium Count Summary"],
        fields,
        percent_fields={"motor_average_rate_2026", "motor_average_rate_2025"},
    )


def extract_status_mix(df):
    status = {"2025": [], "2026": []}
    current_year = None
    start = find_row(df, "2025", col=2) or 38
    for ridx in range(start, min(len(df), start + 30)):
        label = clean_name(df.iat[ridx, 2])
        if label in {"2025", "2026"}:
            current_year = label
            continue
        if label in MONTH_ORDER and current_year:
            status[current_year].append(
                {
                    "month": label,
                    "collection": parse_number(df.iat[ridx, 3]),
                    "endorsement": parse_number(df.iat[ridx, 4]),
                    "new": parse_number(df.iat[ridx, 5]),
                    "renewal": parse_number(df.iat[ridx, 6]),
                    "grand_total": parse_number(df.iat[ridx, 7]),
                }
            )
    return status


def extract_insurers(df):
    records = []
    total = None
    header_row = find_row(df, "Insurance Company", col=9) or 37
    for ridx in range(header_row + 1, len(df)):
        name = clean_name(df.iat[ridx, 9])
        if not name:
            if records:
                break
            continue
        premium_2025 = parse_number(df.iat[ridx, 10])
        premium_2026 = parse_number(df.iat[ridx, 11])
        rec = {
            "insurance_company": name,
            "premium_2025": premium_2025,
            "premium_2026": premium_2026,
            "yoy_change": premium_2026 - premium_2025 if premium_2026 is not None and premium_2025 is not None else None,
            "yoy_change_pct": safe_yoy(premium_2026, premium_2025),
            "source_yoy_change": parse_number(df.iat[ridx, 12]),
            "source_yoy_change_pct": parse_percent(df.iat[ridx, 13]),
        }
        if name.lower() == "grand total":
            total = rec
            break
        elif not is_total_label(name):
            records.append(rec)
    total_2026 = total["premium_2026"] if total else sum(money(r["premium_2026"]) for r in records)
    for rec in records:
        rec["share_2026_pct"] = safe_div(rec["premium_2026"], total_2026)
        rec["new_2026_base"] = (rec["premium_2025"] in (None, 0)) and money(rec["premium_2026"]) != 0
        rec["growth_class"] = classify_yoy(rec["premium_2025"], rec["premium_2026"])
    return records, total


def extract_lob_totals(df):
    records = []
    total = None
    start = find_row(df, "Line of Business", col=2)
    if start is None:
        start = find_row(df, "H1 YOY by Line of Business", col=2)
    if start is None:
        start = 260
    header_row = find_row(df, "Month", start=start, col=2)
    if header_row is None:
        header_row = start
    for ridx in range(header_row + 1, len(df)):
        lob = clean_name(df.iat[ridx, 2])
        if not lob:
            if records:
                break
            continue
        rec = {
            "line_of_business": lob,
            "premium_2025": parse_number(df.iat[ridx, 3]),
            "target_2026": parse_number(df.iat[ridx, 4]),
            "premium_2026": parse_number(df.iat[ridx, 5]),
            "source_target_achievement_pct": parse_percent(df.iat[ridx, 6]),
            "source_yoy_change": parse_number(df.iat[ridx, 7]),
            "new_premium": parse_number(df.iat[ridx, 8]),
            "renewal_premium": parse_number(df.iat[ridx, 9]),
            "endorsement_premium": parse_number(df.iat[ridx, 10]),
            "motor_premium": parse_number(df.iat[ridx, 11]),
            "non_motor_premium": parse_number(df.iat[ridx, 12]),
            "pending_finance": parse_number(df.iat[ridx, 13]),
        }
        rec["yoy_change"] = (
            rec["premium_2026"] - rec["premium_2025"]
            if rec["premium_2026"] is not None and rec["premium_2025"] is not None
            else None
        )
        rec["target_achievement_pct"] = safe_div(rec["premium_2026"], rec["target_2026"])
        rec["yoy_change_pct"] = safe_yoy(rec["premium_2026"], rec["premium_2025"])
        rec["new_2026_base"] = (rec["premium_2025"] in (None, 0)) and money(rec["premium_2026"]) != 0
        if lob.lower() == "grand total":
            total = rec
            break
        elif not is_total_label(lob):
            records.append(rec)
    total_2026 = total["premium_2026"] if total else sum(money(r["premium_2026"]) for r in records)
    for rec in records:
        rec["share_2026_pct"] = safe_div(rec["premium_2026"], total_2026)
        rec["growth_class"] = classify_yoy(rec["premium_2025"], rec["premium_2026"])
    return records, total


def extract_lob_monthly(df):
    records = []
    month_index = 0
    month = MONTH_ORDER[month_index]
    start = find_row(df, "Monthly Breakdown By Line of Business", col=2)
    header_row = find_row(df, "Month", start=start or 80, col=2) or 85
    for ridx in range(header_row + 1, len(df)):
        label = clean_name(df.iat[ridx, 2])
        if not label:
            if records and month_index >= len([m for m in MONTH_ORDER if any(r["month"] == m for r in records)]) - 1:
                continue
            continue
        if label.endswith("Total"):
            expected = f"{month} Total" if month else ""
            if label == expected and month_index < len(MONTH_ORDER) - 1:
                month_index += 1
                month = MONTH_ORDER[month_index]
            elif label == "Grand Total":
                break
            continue
        if label == "H1 YOY by Line of Business":
            break
        if month:
            value_2026 = parse_number(df.iat[ridx, 5])
            if value_2026 is not None:
                records.append(
                    {
                        "month": month,
                        "line_of_business": label,
                        "premium_2026": value_2026,
                        "premium_2025": parse_number(df.iat[ridx, 3]),
                        "new_premium": parse_number(df.iat[ridx, 8]),
                        "renewal_premium": parse_number(df.iat[ridx, 9]),
                    }
                )
    return records


def build_insights(data):
    k = data["kpis"]
    monthly = data["monthly"]
    branches = data["branches"]
    sellers = data["sellers"]
    insurers = data["insurers"]
    lobs = data["lines_of_business"]
    total = data["totals"]

    best_month = max(monthly, key=lambda r: money(r["actual_2026"]))
    best_achievement = max(monthly, key=lambda r: money(r["target_achievement_pct"]))
    weakest_month = min(monthly, key=lambda r: money(r["actual_2026"]))
    top_branch = max(branches, key=lambda r: money(r["premium_2026"]))
    top_seller = max(sellers, key=lambda r: money(r["premium_2026"])) if sellers else None
    top3_share = data["summary_metrics"]["top3_insurer_share_pct"]
    top_lob = max(lobs, key=lambda r: money(r["premium_2026"]))
    positive_branches = [r for r in branches if r.get("growth_class") == "Positive Growth"]
    highest_pending = max(branches, key=lambda r: money(r["pending_total"]))
    renewal_total = next((r for r in data["renewals"] if r["month"] == "Grand Total"), None)

    return {
        "positive_highlights": [
            f"{best_achievement['month']} delivered the strongest target achievement at {format_percent(best_achievement['target_achievement_pct'])}, supported by {format_money(best_achievement['actual_2026'], compact=True)} in approved premium.",
            f"{top_branch['branch']} was the leading branch with {format_money(top_branch['premium_2026'], compact=True)}, contributing {format_percent(top_branch['contribution_pct'])} of approved premium.",
            f"{len(positive_branches)} branches grew year over year, led by {max(positive_branches, key=lambda r: money(r['yoy_change']))['branch']} in absolute growth." if positive_branches else "No branch recorded positive year-over-year premium growth.",
        ],
        "key_concerns": [
            f"Approved gross premium declined {format_percent(k['Approved Gross Premiums']['change_pct'])} versus YTD 2025, a decrease of {format_money(abs(k['Approved Gross Premiums']['change']), compact=True)}.",
            f"Target achievement reached {format_percent(total['target_achievement_pct'])}, leaving {format_money(total['target_gap'], compact=True)} below the YTD 2026 target.",
            f"{weakest_month['month']} was the weakest month at {format_money(weakest_month['actual_2026'], compact=True)} and only {format_percent(weakest_month['target_achievement_pct'])} of target.",
            f"The top three insurers represented {format_percent(top3_share)} of YTD 2026 approved premium, creating concentration exposure.",
        ],
        "opportunities": [
            f"Pending pipeline totals {format_money(total['pending_total'], compact=True)}, equal to {format_percent(total['pending_as_pct_approved'])} of approved premium.",
            f"{top_lob['line_of_business']} remains the largest line at {format_money(top_lob['premium_2026'], compact=True)}; improving its conversion has the highest near-term impact.",
            f"Motor renewal rate was {format_percent(renewal_total['renewal_rate'])} across YTD, leaving {format_count(renewal_total['not_renewed_policies'])} not-renewed policies as a recovery pool." if renewal_total else "Renewal-rate opportunity could not be calculated from the available workbook data.",
            f"{top_seller['seller']} led seller production at {format_money(top_seller['premium_2026'], compact=True)}; top-seller practices should be replicated across declining sellers." if top_seller else "Seller-level opportunities are limited because only the workbook's top-seller section is available.",
        ],
    }


def build_recommendations(data):
    branches = data["branches"]
    sellers = data["sellers"]
    insurers = data["insurers"]
    monthly = data["monthly"]
    lobs = data["lines_of_business"]
    total = data["totals"]
    renewal_total = next((r for r in data["renewals"] if r["month"] == "Grand Total"), None)
    highest_pending = max(branches, key=lambda r: money(r["pending_total"]))
    weakest_month = min(monthly, key=lambda r: money(r["target_achievement_pct"]))
    largest_decline_branch = min(branches, key=lambda r: money(r["yoy_change"]))
    motor_lob = max(lobs, key=lambda r: money(r["motor_premium"]))
    top_seller = max(sellers, key=lambda r: money(r["premium_2026"])) if sellers else None
    top3_share = data["summary_metrics"]["top3_insurer_share_pct"]

    rows = [
        {
            "priority": "P1",
            "action": "Close the YTD target gap with branch-level recovery plans.",
            "evidence": f"YTD achievement is {format_percent(total['target_achievement_pct'])}, leaving {format_money(total['target_gap'], compact=True)} below target.",
            "kpi": "Target achievement %, approved premium gap",
        },
        {
            "priority": "P1",
            "action": "Convert pending pipeline starting with the largest exposed branches.",
            "evidence": f"{highest_pending['branch']} has {format_money(highest_pending['pending_total'], compact=True)} pending exposure.",
            "kpi": "Pending conversion value, pending aging",
        },
        {
            "priority": "P2",
            "action": "Recover high-value declining branches through account-level action reviews.",
            "evidence": f"{largest_decline_branch['branch']} declined by {format_money(abs(largest_decline_branch['yoy_change']), compact=True)} YoY.",
            "kpi": "Branch YoY change, branch win-back premium",
        },
        {
            "priority": "P2",
            "action": "Improve motor renewal conversion and follow up not-renewed policies.",
            "evidence": f"YTD renewal rate is {format_percent(renewal_total['renewal_rate'])} with {format_count(renewal_total['not_renewed_policies'])} not-renewed policies." if renewal_total else "Renewal policy totals are available only in aggregate.",
            "kpi": "Renewal rate, not-renewed policies",
        },
        {
            "priority": "P2",
            "action": "Reduce motor concentration by expanding non-motor cross-sell.",
            "evidence": f"{motor_lob['line_of_business']} contributes {format_money(motor_lob['premium_2026'], compact=True)} of approved premium.",
            "kpi": "Non-motor premium share, cross-sell premium",
        },
        {
            "priority": "P3",
            "action": "Manage insurer concentration and broaden active insurer participation.",
            "evidence": f"Top three insurers account for {format_percent(top3_share)} of approved premium.",
            "kpi": "Top-3 insurer share, insurer active count",
        },
        {
            "priority": "P3",
            "action": "Replicate top-seller practices in lower-performing seller cohorts.",
            "evidence": f"{top_seller['seller']} produced {format_money(top_seller['premium_2026'], compact=True)}." if top_seller else "Seller analysis is limited to the workbook's top 20 sellers.",
            "kpi": "Seller premium, average premium per policy",
        },
        {
            "priority": "P3",
            "action": "Investigate weak monthly cadence and set early-warning triggers.",
            "evidence": f"{weakest_month['month']} achieved only {format_percent(weakest_month['target_achievement_pct'])} of target.",
            "kpi": "Monthly achievement %, monthly YoY %",
        },
    ]
    return rows


def reconciliation(data):
    approved = data["totals"]["approved_gross_premium"]
    monthly_sum = sum(money(r["actual_2026"]) for r in data["monthly"])
    branch_sum = sum(money(r["premium_2026"]) for r in data["branches"])
    lob_sum = sum(money(r["premium_2026"]) for r in data["lines_of_business"])
    insurer_sum = sum(money(r["premium_2026"]) for r in data["insurers"])
    return {
        "approved_gross_premium": approved,
        "monthly_sum_2026": monthly_sum,
        "monthly_difference": monthly_sum - approved,
        "branch_sum_2026": branch_sum,
        "branch_difference": branch_sum - approved,
        "line_of_business_sum_2026": lob_sum,
        "line_of_business_difference": lob_sum - approved,
        "insurer_sum_2026": insurer_sum,
        "insurer_difference": insurer_sum - approved,
    }


def build_policy_type_mix(totals):
    other = money(totals["approved_gross_premium"]) - money(totals["new_premium"]) - money(totals["renewal_premium"])
    totals["other_policy_types_premium"] = other
    return [
        {"category": "New Premium", "premium": totals["new_premium"]},
        {"category": "Renewal Premium", "premium": totals["renewal_premium"]},
        {"category": "Other Policy Types", "premium": other},
    ]


def build_pending_categories(totals):
    return [
        {"category": "Operation Paid", "premium": totals["pending_operation_paid"]},
        {"category": "Pending Finance", "premium": totals["pending_finance"]},
        {"category": "Pending Payment", "premium": totals["pending_payment"]},
    ]


PREMIUM_BINS = [
    {"label": "No Production", "min": None, "max": 0, "kind": "no-production"},
    {"label": "EGP 0-50K", "min": 0, "max": 50_000},
    {"label": "EGP 50K-100K", "min": 50_000, "max": 100_000},
    {"label": "EGP 100K-150K", "min": 100_000, "max": 150_000},
    {"label": "EGP 150K-200K", "min": 150_000, "max": 200_000},
    {"label": "EGP 200K-300K", "min": 200_000, "max": 300_000},
    {"label": "EGP 300K-600K", "min": 300_000, "max": 600_000},
    {"label": "EGP 600K-900K", "min": 600_000, "max": 900_000},
    {"label": "EGP 900K-1.2M", "min": 900_000, "max": 1_200_000},
    {"label": "EGP 1.2M-1.5M", "min": 1_200_000, "max": 1_500_000},
    {"label": "EGP 1.5M-1.8M", "min": 1_500_000, "max": 1_800_000},
    {"label": "EGP 1.8M-2.1M", "min": 1_800_000, "max": 2_100_000},
    {"label": "EGP 2.1M-2.4M", "min": 2_100_000, "max": 2_400_000},
    {"label": "EGP 2.4M-2.7M", "min": 2_400_000, "max": 2_700_000},
    {"label": "EGP 2.7M-3.0M", "min": 2_700_000, "max": 3_000_000, "include_max": True},
    {"label": "More than EGP 3.0M", "min": 3_000_000, "max": None, "kind": "overflow"},
]


def build_premium_distribution(branches):
    bins = [{**b, "count": 0} for b in PREMIUM_BINS]
    for branch in branches:
        premium = branch.get("premium_2026")
        assigned = False
        for bin_item in bins:
            if bin_item.get("kind") == "no-production":
                if premium is None or money(premium) <= 0:
                    bin_item["count"] += 1
                    assigned = True
                    break
                continue
            if bin_item.get("kind") == "overflow":
                if money(premium) > bin_item["min"]:
                    bin_item["count"] += 1
                    assigned = True
                    break
                continue
            lower_ok = money(premium) > 0 if bin_item["min"] == 0 else money(premium) >= bin_item["min"]
            if premium is not None and lower_ok and (
                money(premium) <= bin_item["max"] if bin_item.get("include_max") else money(premium) < bin_item["max"]
            ):
                bin_item["count"] += 1
                assigned = True
                break
        if not assigned:
            bins[0]["count"] += 1
    return bins


def metric_slug(value):
    return re.sub(r"[^a-z0-9]+", "-", clean_name(value).lower()).strip("-")


def register_rate(registry, metric_id, label, numerator, denominator, decimals=1, source_rate=None):
    result = registry.register(
        metric_id,
        label,
        numerator,
        denominator,
        decimals=decimals,
        source_rate=source_rate,
    )
    return float(result) if result is not None else None


def build_metric_catalog(data):
    registry = MetricRegistry()
    approved = data["totals"]["approved_gross_premium"]

    for name, record in data["kpis"].items():
        record["change_pct"] = register_rate(
            registry,
            f"kpi.{metric_slug(name)}.yoy",
            f"{name} YoY",
            record["change"],
            record["value_2025"],
            source_rate=record.get("source_change_pct"),
        )

    for record in [*data["monthly"], data["monthly_total"]]:
        month = record["month"]
        record["target_achievement_pct"] = register_rate(
            registry,
            f"monthly.{month}.target_achievement",
            f"{month} Target Achievement",
            record["actual_2026"],
            record["target_2026"],
            source_rate=record.get("source_target_achievement_pct"),
        )
        yoy_change = (
            record["actual_2026"] - record["actual_2025"]
            if record["actual_2026"] is not None and record["actual_2025"] is not None
            else None
        )
        record["yoy_pct"] = register_rate(
            registry,
            f"monthly.{month}.yoy",
            f"{month} YoY",
            yoy_change,
            record["actual_2025"],
        )

    for record in [*data["monthly_count_summary"], data["monthly_count_total"]]:
        month = record["month"]
        for year in (2025, 2026):
            key = f"motor_average_rate_{year}"
            source_rate = record.get(key)
            record[key] = register_rate(
                registry,
                f"monthly-count.{month}.motor_average_rate_{year}",
                f"{month} Motor Average Rate {year}",
                source_rate,
                1,
                decimals=2,
                source_rate=source_rate,
            )

    def register_entity(records, area, name_key, contribution_denominator=None):
        for record in records:
            name = record[name_key]
            identity = f"{name}-{record['month']}" if record.get("month") else name
            display_name = f"{name} {record['month']}" if record.get("month") else name
            prefix = f"{area}.{metric_slug(identity)}"
            record["yoy_change_pct"] = register_rate(
                registry,
                f"{prefix}.yoy",
                f"{display_name} YoY",
                record.get("yoy_change"),
                record.get("premium_2025"),
                source_rate=record.get("source_yoy_change_pct"),
            )
            if contribution_denominator is not None:
                record["contribution_pct"] = register_rate(
                    registry,
                    f"{prefix}.contribution",
                    f"{display_name} Contribution",
                    record.get("premium_2026"),
                    contribution_denominator,
                )
            record["renewal_mix_pct"] = register_rate(
                registry,
                f"{prefix}.renewal_mix",
                f"{display_name} Renewal Mix",
                record.get("renewal_premium"),
                record.get("premium_2026"),
            )
            record["motor_mix_pct"] = register_rate(
                registry,
                f"{prefix}.motor_mix",
                f"{display_name} Motor Mix",
                record.get("motor_premium"),
                record.get("premium_2026"),
            )

    register_entity(data["branches"], "branch", "branch", approved)
    register_entity(data["branch_monthly"], "branch-monthly", "branch")
    register_entity(data["sellers"], "seller", "seller", sum(money(r["premium_2026"]) for r in data["sellers"]))

    insurer_total = sum(money(r["premium_2026"]) for r in data["insurers"])
    for record in data["insurers"]:
        name = record["insurance_company"]
        prefix = f"insurer.{metric_slug(name)}"
        record["yoy_change_pct"] = register_rate(
            registry,
            f"{prefix}.yoy",
            f"{name} YoY",
            record.get("yoy_change"),
            record.get("premium_2025"),
            source_rate=record.get("source_yoy_change_pct"),
        )
        record["share_2026_pct"] = register_rate(
            registry,
            f"{prefix}.share",
            f"{name} 2026 Share",
            record.get("premium_2026"),
            insurer_total,
        )

    lob_total = sum(money(r["premium_2026"]) for r in data["lines_of_business"])
    for record in data["lines_of_business"]:
        name = record["line_of_business"]
        prefix = f"lob.{metric_slug(name)}"
        record["target_achievement_pct"] = register_rate(
            registry,
            f"{prefix}.target_achievement",
            f"{name} Target Achievement",
            record.get("premium_2026"),
            record.get("target_2026"),
            source_rate=record.get("source_target_achievement_pct"),
        )
        record["yoy_change_pct"] = register_rate(
            registry,
            f"{prefix}.yoy",
            f"{name} YoY",
            record.get("yoy_change"),
            record.get("premium_2025"),
        )
        record["share_2026_pct"] = register_rate(
            registry,
            f"{prefix}.share",
            f"{name} 2026 Share",
            record.get("premium_2026"),
            lob_total,
        )

    for record in data["renewals"]:
        record["renewal_rate"] = register_rate(
            registry,
            f"renewal.{record['month']}.rate",
            f"{record['month']} Renewal Rate",
            record.get("renewed_policies"),
            record.get("policies_up_for_renewal"),
        )

    totals = data["totals"]
    totals["target_achievement_pct"] = register_rate(
        registry,
        "totals.target_achievement",
        "Overall Target Achievement",
        approved,
        totals["target_2026"],
        source_rate=data["monthly_total"].get("source_target_achievement_pct"),
    )
    totals["target_variance_pct"] = register_rate(
        registry,
        "totals.target_variance",
        "Target Variance",
        approved - totals["target_2026"],
        totals["target_2026"],
    )
    totals["pending_as_pct_approved"] = register_rate(
        registry,
        "totals.pending_share",
        "Pending as Share of Approved Premium",
        totals["pending_total"],
        approved,
    )
    for key, label in (
        ("new_premium", "New Premium Mix"),
        ("renewal_premium", "Renewal Premium Mix"),
        ("other_policy_types_premium", "Other Policy Types Mix"),
    ):
        totals[f"{key}_mix_pct"] = register_rate(
            registry,
            f"totals.{key}_mix",
            label,
            totals[key],
            approved,
        )

    top3_premium = sum(
        money(record["premium_2026"])
        for record in sorted(data["insurers"], key=lambda item: money(item["premium_2026"]), reverse=True)[:3]
    )
    data["summary_metrics"] = {
        "top3_insurer_share_pct": register_rate(
            registry,
            "insurers.top3_share",
            "Top 3 Insurer Share",
            top3_premium,
            approved,
        )
    }
    return registry


def make_check(name, expected, actual, tolerance=1, severity="error"):
    difference = money(actual) - money(expected)
    status = "pass" if abs(difference) <= tolerance else severity
    return {
        "name": name,
        "status": status,
        "expected": expected,
        "actual": actual,
        "difference": difference,
        "tolerance": tolerance,
    }


def validate_report(data):
    totals = data["totals"]
    approved = totals["approved_gross_premium"]
    checks = [
        make_check("Monthly totals = overall total", approved, sum(money(r["actual_2026"]) for r in data["monthly"])),
        make_check(
            "Monthly amount rows = workbook grand total",
            data["monthly_total"]["actual_2026"],
            sum(money(r["actual_2026"]) for r in data["monthly"]),
        ),
        make_check(
            "Monthly count rows = workbook grand total",
            data["monthly_count_total"]["total_policies_2026"],
            sum(money(r["total_policies_2026"]) for r in data["monthly_count_summary"]),
            tolerance=0,
        ),
        make_check("Branch totals = overall total", approved, sum(money(r["premium_2026"]) for r in data["branches"])),
        make_check("Line-of-business totals = overall total", approved, sum(money(r["premium_2026"]) for r in data["lines_of_business"])),
        make_check("Insurer totals = overall total", approved, sum(money(r["premium_2026"]) for r in data["insurers"])),
        make_check("Pending category totals = total pending", totals["pending_total"], sum(money(r["premium"]) for r in data["pending_categories"])),
        make_check("Policy-type premium totals = approved gross premium", approved, sum(money(r["premium"]) for r in data["policy_type_mix"])),
        make_check("Premium distribution branch counts = unique branches", len(data["branches"]), sum(int(r["count"]) for r in data["premium_distribution_bins"]), tolerance=0),
    ]
    for renewal in data["renewals"]:
        checks.append(
            make_check(
                f"Renewal counts reconcile - {renewal['month']}",
                renewal["policies_up_for_renewal"],
                money(renewal["renewed_policies"]) + money(renewal["not_renewed_policies"]),
                tolerance=0,
            )
        )
    checks.append(make_check("Branch contribution shares total 100%", 1, sum(money(r["contribution_pct"]) for r in data["branches"]), tolerance=0.0001))
    checks.append(make_check("LOB shares total 100%", 1, sum(money(r["share_2026_pct"]) for r in data["lines_of_business"]), tolerance=0.0001))
    checks.append(make_check("Insurer shares total 100%", 1, sum(money(r["share_2026_pct"]) for r in data["insurers"]), tolerance=0.0001))

    issues = [c for c in checks if c["status"] != "pass"]
    return {
        "status": "pass" if not issues else "fail",
        "checks": checks,
        "issues": issues,
    }


def main():
    if not WORKBOOK.exists():
        raise FileNotFoundError(WORKBOOK)

    overview = pd.read_excel(WORKBOOK, sheet_name="overview", header=None, engine="openpyxl")
    branches_sheet = pd.read_excel(WORKBOOK, sheet_name="Branches", header=None, engine="openpyxl")

    kpis = extract_kpis(overview)
    renewals = extract_renewals(overview)
    monthly, monthly_total = extract_monthly(overview)
    monthly_counts, monthly_count_total = extract_monthly_counts(overview)
    status_mix = extract_status_mix(overview)
    insurers, insurer_total = extract_insurers(overview)
    lobs, lob_total = extract_lob_totals(overview)
    lob_monthly = extract_lob_monthly(overview)
    branches, branch_total, branch_monthly = extract_branch_breakdown(branches_sheet)
    sellers, seller_total = extract_sellers(branches_sheet)
    branches_per_month = extract_branches_per_month(branches_sheet)

    approved = kpis["Approved Gross Premiums"]["value_2026"]
    target = monthly_total["target_2026"]
    pending_operation_paid = branch_total["pending_operation_paid"]
    pending_finance = branch_total["pending_finance"]
    pending_payment = branch_total["pending_payment"]
    pending_total = money(pending_operation_paid) + money(pending_finance) + money(pending_payment)

    totals = {
        "approved_gross_premium": approved,
        "approved_gross_premium_2025": kpis["Approved Gross Premiums"]["value_2025"],
        "target_2026": target,
        "target_achievement_pct": monthly_total["target_achievement_pct"],
        "target_gap": target - approved,
        "total_policies": kpis["Total Policies"]["value_2026"],
        "approved_policies": kpis["Total Approved Policies"]["value_2026"],
        "avg_premium_per_policy": kpis["Avg Premium per policy"]["value_2026"],
        "new_premium": monthly_total["new_premium"],
        "renewal_premium": monthly_total["renewal_premium"],
        "endorsement_premium": monthly_total["endorsement_premium"],
        "motor_premium": monthly_total["motor_premium"],
        "non_motor_premium": monthly_total["non_motor_premium"],
        "pending_operation_paid": pending_operation_paid,
        "pending_finance": pending_finance,
        "pending_payment": pending_payment,
        "pending_total": pending_total,
        "pending_as_pct_approved": safe_div(pending_total, approved),
    }
    policy_type_mix = build_policy_type_mix(totals)
    pending_categories = build_pending_categories(totals)
    premium_distribution_bins = build_premium_distribution(branches)
    reporting_months = [r["month"] for r in monthly if r["month"] in MONTH_ORDER and money(r["actual_2026"]) != 0]
    reporting_period = month_range_label(reporting_months)

    data = {
        "meta": {
            "title": "Contact Branches Performance",
            "subtitle": "YTD 2026 Executive Report",
            "reporting_period": reporting_period,
            "reporting_months": reporting_months,
            "latest_reporting_month": reporting_months[-1] if reporting_months else None,
            "last_updated": date.today().isoformat(),
            "source": WORKBOOK.name,
            "generated_by": "analysis.py",
        },
        "kpis": kpis,
        "totals": totals,
        "monthly": monthly,
        "monthly_total": monthly_total,
        "monthly_count_summary": monthly_counts,
        "monthly_count_total": monthly_count_total,
        "status_mix": status_mix,
        "branches": branches,
        "branch_monthly": branch_monthly,
        "branches_per_month": branches_per_month,
        "sellers": sellers,
        "insurers": insurers,
        "lines_of_business": lobs,
        "line_of_business_monthly": lob_monthly,
        "renewals": renewals,
        "policy_type_mix": policy_type_mix,
        "pending_categories": pending_categories,
        "premium_distribution_bins": premium_distribution_bins,
        "management_actions": [],
        "insights": {},
        "data_quality_notes": [
            "Workbook values include formatted text such as EGP amounts, percentages, blanks, and parentheses for negatives; analysis.py converts these before calculation.",
            "Grand Total, month total, and year total rows are excluded from rankings and retained only for reconciliation.",
            "Seller data comes from the workbook's Top 20 seller section, not a complete all-seller extract.",
            "Renewal-rate analysis is based on aggregated monthly workbook counts; policy-level renewal aging and reasons for non-renewal are not available.",
            "Pending values are reported separately from approved premium and are not added to approved production.",
            "Some percentage fields are mixed between decimal and formatted percentage text; all are normalized to decimal rates in JSON.",
            "Rows with no prior-year base are labeled separately so high growth from a tiny or blank base is not overstated.",
            "Possible spelling inconsistencies are retained as provided by the workbook, including 'Renew Premuims'.",
        ],
    }
    registry = build_metric_catalog(data)
    data["calculated_metrics"] = registry.to_json()
    data["insights"] = build_insights(data)
    data["management_actions"] = build_recommendations(data)
    data["reconciliation"] = reconciliation(data)
    data["validation"] = validate_report(data)

    json_text = json.dumps(data, ensure_ascii=False, indent=2)
    (DATA_DIR / "report-data.json").write_text(json_text, encoding="utf-8")
    (DATA_DIR / "report-data.js").write_text("window.REPORT_DATA = " + json_text + ";\n", encoding="utf-8")
    (DATA_DIR / "validation-summary.json").write_text(json.dumps(data["validation"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {DATA_DIR / 'report-data.json'}")
    print(json.dumps(data["reconciliation"], indent=2))
    print(json.dumps(data["validation"], indent=2))


if __name__ == "__main__":
    main()
