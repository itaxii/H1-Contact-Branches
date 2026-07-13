import json
import math
import re
from datetime import date
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
WORKBOOK = BASE_DIR.parent / "H1 Contact Branches v2.xlsx"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


MONTH_ORDER = ["January", "February", "March", "April", "May", "June"]
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
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def money(value):
    return 0 if value is None else float(value)


def row_to_record(row, cols, name_key):
    record = {name_key: clean_name(row.iloc[cols[0]])}
    record.update(
        {
            "premium_2025": parse_number(row.iloc[cols[1]]),
            "premium_2026": parse_number(row.iloc[cols[2]]),
            "yoy_change": parse_number(row.iloc[cols[3]]),
            "yoy_change_pct": parse_percent(row.iloc[cols[4]]),
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
    record["contribution_pct"] = None
    record["avg_premium_per_policy"] = safe_div(record["premium_2026"], record["approved_policies"])
    record["renewal_mix_pct"] = safe_div(record["renewal_premium"], record["premium_2026"])
    record["motor_mix_pct"] = safe_div(record["motor_premium"], record["premium_2026"])
    record["pending_total"] = sum(money(record[k]) for k in ["pending_operation_paid", "pending_finance", "pending_payment"])
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


def extract_kpis(df):
    kpis = {}
    for ridx in range(12, 20):
        name = clean_name(df.iat[ridx, 2])
        if not name:
            continue
        kpis[name] = {
            "label": name,
            "value_2025": parse_number(df.iat[ridx, 3]),
            "value_2026": parse_number(df.iat[ridx, 4]),
            "change": parse_number(df.iat[ridx, 5]),
            "change_pct": parse_percent(df.iat[ridx, 6]),
        }
    return kpis


def extract_renewals(df):
    records = []
    for ridx in range(13, 20):
        month = clean_name(df.iat[ridx, 9])
        if month not in MONTH_ORDER and month != "Grand Total":
            continue
        renewed = parse_number(df.iat[ridx, 10])
        up_for_renewal = parse_number(df.iat[ridx, 11])
        rate = parse_percent(df.iat[ridx, 12])
        records.append(
            {
                "month": month,
                "renewed_policies": renewed,
                "policies_up_for_renewal": up_for_renewal,
                "not_renewed_policies": None if renewed is None or up_for_renewal is None else up_for_renewal - renewed,
                "renewal_rate": rate,
            }
        )
    return records


def extract_monthly(df):
    records = []
    total = None
    for ridx in range(68, 75):
        month = clean_name(df.iat[ridx, 2])
        rec = {
            "month": month,
            "actual_2025": parse_number(df.iat[ridx, 3]),
            "target_2026": parse_number(df.iat[ridx, 4]),
            "actual_2026": parse_number(df.iat[ridx, 5]),
            "target_achievement_pct": parse_percent(df.iat[ridx, 6]),
            "yoy_change": parse_number(df.iat[ridx, 7]),
            "new_premium": parse_number(df.iat[ridx, 8]),
            "renewal_premium": parse_number(df.iat[ridx, 9]),
            "endorsement_premium": parse_number(df.iat[ridx, 10]),
            "motor_premium": parse_number(df.iat[ridx, 11]),
            "non_motor_premium": parse_number(df.iat[ridx, 12]),
            "pending_finance": parse_number(df.iat[ridx, 13]),
        }
        rec["yoy_pct"] = safe_div(rec["actual_2026"] - rec["actual_2025"], rec["actual_2025"]) if rec["actual_2025"] else None
        if month == "Grand Total":
            total = rec
        else:
            records.append(rec)
    return records, total


def extract_status_mix(df):
    status = {"2025": [], "2026": []}
    current_year = None
    for ridx in range(38, 54):
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
    for ridx in range(38, 53):
        name = clean_name(df.iat[ridx, 9])
        if not name:
            continue
        rec = {
            "insurance_company": name,
            "premium_2025": parse_number(df.iat[ridx, 10]),
            "premium_2026": parse_number(df.iat[ridx, 11]),
            "yoy_change": parse_number(df.iat[ridx, 12]),
            "yoy_change_pct": parse_percent(df.iat[ridx, 13]),
        }
        if name.lower() == "grand total":
            total = rec
        elif not is_total_label(name):
            records.append(rec)
    total_2026 = total["premium_2026"] if total else sum(money(r["premium_2026"]) for r in records)
    for rec in records:
        rec["share_2026_pct"] = safe_div(rec["premium_2026"], total_2026)
        rec["new_2026_base"] = (rec["premium_2025"] in (None, 0)) and money(rec["premium_2026"]) != 0
    return records, total


def extract_lob_totals(df):
    records = []
    total = None
    for ridx in range(231, 259):
        lob = clean_name(df.iat[ridx, 2])
        if not lob:
            continue
        rec = {
            "line_of_business": lob,
            "premium_2025": parse_number(df.iat[ridx, 3]),
            "target_2026": parse_number(df.iat[ridx, 4]),
            "premium_2026": parse_number(df.iat[ridx, 5]),
            "target_achievement_pct": parse_percent(df.iat[ridx, 6]),
            "yoy_change": parse_number(df.iat[ridx, 7]),
            "new_premium": parse_number(df.iat[ridx, 8]),
            "renewal_premium": parse_number(df.iat[ridx, 9]),
            "endorsement_premium": parse_number(df.iat[ridx, 10]),
            "motor_premium": parse_number(df.iat[ridx, 11]),
            "non_motor_premium": parse_number(df.iat[ridx, 12]),
            "pending_finance": parse_number(df.iat[ridx, 13]),
        }
        rec["yoy_change_pct"] = (
            safe_div(money(rec["premium_2026"]) - money(rec["premium_2025"]), rec["premium_2025"])
            if rec["premium_2025"] not in (None, 0)
            else None
        )
        rec["new_2026_base"] = (rec["premium_2025"] in (None, 0)) and money(rec["premium_2026"]) != 0
        if lob.lower() == "grand total":
            total = rec
        elif not is_total_label(lob):
            records.append(rec)
    total_2026 = total["premium_2026"] if total else sum(money(r["premium_2026"]) for r in records)
    for rec in records:
        rec["share_2026_pct"] = safe_div(rec["premium_2026"], total_2026)
    return records, total


def extract_lob_monthly(df):
    records = []
    month_index = 0
    month = MONTH_ORDER[month_index]
    for ridx in range(86, 218):
        label = clean_name(df.iat[ridx, 2])
        if not label:
            continue
        if label.endswith("Total"):
            expected = f"{month} Total" if month else ""
            if label == expected and month_index < len(MONTH_ORDER) - 1:
                month_index += 1
                month = MONTH_ORDER[month_index]
            continue
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
    top_insurers = sorted(insurers, key=lambda r: money(r["premium_2026"]), reverse=True)[:3]
    top3_share = sum(money(r["premium_2026"]) for r in top_insurers) / money(total["approved_gross_premium"])
    top_lob = max(lobs, key=lambda r: money(r["premium_2026"]))
    positive_branches = [r for r in branches if money(r["yoy_change"]) > 0]
    highest_pending = max(branches, key=lambda r: money(r["pending_total"]))
    renewal_total = next((r for r in data["renewals"] if r["month"] == "Grand Total"), None)

    return {
        "positive_highlights": [
            f"{best_achievement['month']} delivered the strongest target achievement at {best_achievement['target_achievement_pct']:.1%}, supported by EGP {best_achievement['actual_2026']/1_000_000:.1f}M in approved premium.",
            f"{top_branch['branch']} was the leading branch with EGP {top_branch['premium_2026']/1_000_000:.1f}M, contributing {top_branch['contribution_pct']:.1%} of approved premium.",
            f"{len(positive_branches)} branches grew year over year, led by {max(positive_branches, key=lambda r: money(r['yoy_change']))['branch']} in absolute growth." if positive_branches else "No branch recorded positive year-over-year premium growth.",
        ],
        "key_concerns": [
            f"Approved gross premium declined {k['Approved Gross Premiums']['change_pct']:.1%} versus H1 2025, a decrease of EGP {abs(k['Approved Gross Premiums']['change'])/1_000_000:.1f}M.",
            f"Target achievement reached {total['target_achievement_pct']:.1%}, leaving EGP {total['target_gap']/1_000_000:.1f}M below the H1 2026 target.",
            f"{weakest_month['month']} was the weakest month at EGP {weakest_month['actual_2026']/1_000_000:.1f}M and only {weakest_month['target_achievement_pct']:.1%} of target.",
            f"The top three insurers represented {top3_share:.1%} of H1 2026 approved premium, creating concentration exposure.",
        ],
        "opportunities": [
            f"Pending pipeline totals EGP {total['pending_total']/1_000_000:.1f}M, equal to {total['pending_as_pct_approved']:.1%} of approved premium.",
            f"{top_lob['line_of_business']} remains the largest line at EGP {top_lob['premium_2026']/1_000_000:.1f}M; improving its conversion has the highest near-term impact.",
            f"Motor renewal rate was {renewal_total['renewal_rate']:.1%} across H1, leaving {renewal_total['not_renewed_policies']:.0f} not-renewed policies as a recovery pool." if renewal_total else "Renewal-rate opportunity could not be calculated from the available workbook data.",
            f"{top_seller['seller']} led seller production at EGP {top_seller['premium_2026']/1_000_000:.1f}M; top-seller practices should be replicated across declining sellers." if top_seller else "Seller-level opportunities are limited because only the workbook's top-seller section is available.",
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
    top_insurers = sorted(insurers, key=lambda r: money(r["premium_2026"]), reverse=True)[:3]
    top3_share = sum(money(r["premium_2026"]) for r in top_insurers) / money(total["approved_gross_premium"])

    rows = [
        {
            "priority": "P1",
            "action": "Close the H1 target gap with branch-level recovery plans.",
            "evidence": f"H1 achievement is {total['target_achievement_pct']:.1%}, leaving EGP {total['target_gap']/1_000_000:.1f}M below target.",
            "kpi": "Target achievement %, approved premium gap",
        },
        {
            "priority": "P1",
            "action": "Convert pending pipeline starting with the largest exposed branches.",
            "evidence": f"{highest_pending['branch']} has EGP {highest_pending['pending_total']/1_000_000:.1f}M pending exposure.",
            "kpi": "Pending conversion value, pending aging",
        },
        {
            "priority": "P2",
            "action": "Recover high-value declining branches through account-level action reviews.",
            "evidence": f"{largest_decline_branch['branch']} declined by EGP {abs(largest_decline_branch['yoy_change'])/1_000_000:.1f}M YoY.",
            "kpi": "Branch YoY change, branch win-back premium",
        },
        {
            "priority": "P2",
            "action": "Improve motor renewal conversion and follow up not-renewed policies.",
            "evidence": f"H1 renewal rate is {renewal_total['renewal_rate']:.1%} with {renewal_total['not_renewed_policies']:.0f} not-renewed policies." if renewal_total else "Renewal policy totals are available only in aggregate.",
            "kpi": "Renewal rate, not-renewed policies",
        },
        {
            "priority": "P2",
            "action": "Reduce motor concentration by expanding non-motor cross-sell.",
            "evidence": f"{motor_lob['line_of_business']} contributes EGP {motor_lob['premium_2026']/1_000_000:.1f}M of approved premium.",
            "kpi": "Non-motor premium share, cross-sell premium",
        },
        {
            "priority": "P3",
            "action": "Manage insurer concentration and broaden active insurer participation.",
            "evidence": f"Top three insurers account for {top3_share:.1%} of approved premium.",
            "kpi": "Top-3 insurer share, insurer active count",
        },
        {
            "priority": "P3",
            "action": "Replicate top-seller practices in lower-performing seller cohorts.",
            "evidence": f"{top_seller['seller']} produced EGP {top_seller['premium_2026']/1_000_000:.1f}M." if top_seller else "Seller analysis is limited to the workbook's top 20 sellers.",
            "kpi": "Seller premium, average premium per policy",
        },
        {
            "priority": "P3",
            "action": "Investigate weak monthly cadence and set early-warning triggers.",
            "evidence": f"{weakest_month['month']} achieved only {weakest_month['target_achievement_pct']:.1%} of target.",
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


def main():
    if not WORKBOOK.exists():
        raise FileNotFoundError(WORKBOOK)

    overview = pd.read_excel(WORKBOOK, sheet_name="overview", header=None, engine="openpyxl")
    branches_sheet = pd.read_excel(WORKBOOK, sheet_name="Branches", header=None, engine="openpyxl")

    kpis = extract_kpis(overview)
    renewals = extract_renewals(overview)
    monthly, monthly_total = extract_monthly(overview)
    status_mix = extract_status_mix(overview)
    insurers, insurer_total = extract_insurers(overview)
    lobs, lob_total = extract_lob_totals(overview)
    lob_monthly = extract_lob_monthly(overview)
    branches, branch_total = extract_entity_table(branches_sheet, 17, 78, "branch")
    sellers, seller_total = extract_entity_table(branches_sheet, 87, 107, "seller")

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

    data = {
        "meta": {
            "title": "Contact Branches Performance",
            "subtitle": "H1 2026 Executive Report",
            "reporting_period": "January-June 2026",
            "last_updated": date.today().isoformat(),
            "source": WORKBOOK.name,
            "generated_by": "analysis.py",
        },
        "kpis": kpis,
        "totals": totals,
        "monthly": monthly,
        "status_mix": status_mix,
        "branches": branches,
        "sellers": sellers,
        "insurers": insurers,
        "lines_of_business": lobs,
        "line_of_business_monthly": lob_monthly,
        "renewals": renewals,
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
    data["insights"] = build_insights(data)
    data["management_actions"] = build_recommendations(data)
    data["reconciliation"] = reconciliation(data)

    json_text = json.dumps(data, ensure_ascii=False, indent=2)
    (DATA_DIR / "report-data.json").write_text(json_text, encoding="utf-8")
    (DATA_DIR / "report-data.js").write_text("window.REPORT_DATA = " + json_text + ";\n", encoding="utf-8")
    print(f"Wrote {DATA_DIR / 'report-data.json'}")
    print(json.dumps(data["reconciliation"], indent=2))


if __name__ == "__main__":
    main()
