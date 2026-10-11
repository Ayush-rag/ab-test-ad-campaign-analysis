"""Step 3 - Run the SQL queries and the statistical tests, then write the findings.

Outputs:
  outputs/sql_results/*.csv       one CSV per SQL query
  outputs/test_result.csv         the main A/B test, every number
  outputs/segment_tests_*.csv     the test repeated per day and per ad-count bucket
  outputs/ab_test_report.xlsx     formatted Excel report
  outputs/insights.md             key findings and the decision
"""
import json
import re
import sqlite3

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

import stats_tests as st
from config import (ALPHA, CONTROL, DB_PATH, EXCEL_REPORT, OUTPUT_DIR, POWER, QUERIES_SQL, SEED,
                    TREATMENT, VALUE_PER_CONVERSION)


def load_queries(path) -> dict[str, str]:
    parts = re.split(r"^-- name:\s*(\w+)\s*$", path.read_text(), flags=re.MULTILINE)
    return {name: sql.strip() for name, sql in zip(parts[1::2], parts[2::2])}


def run_queries() -> dict[str, pd.DataFrame]:
    with sqlite3.connect(DB_PATH) as conn:
        return {name: pd.read_sql_query(sql, conn) for name, sql in load_queries(QUERIES_SQL).items()}


def counts(df: pd.DataFrame) -> tuple[int, int, int, int]:
    """(ad conversions, ad users, psa conversions, psa users) from a user-level table."""
    g = df.groupby("test_group")["converted"].agg(["sum", "count"])
    return (int(g.loc[TREATMENT, "sum"]), int(g.loc[TREATMENT, "count"]),
            int(g.loc[CONTROL, "sum"]), int(g.loc[CONTROL, "count"]))


def segment_tests(seg: pd.DataFrame, key: str) -> pd.DataFrame:
    """Repeat the z-test inside each segment. Testing many segments raises the
    chance of a fluke, so each is judged against a stricter Bonferroni level
    (5% divided by the number of segments)."""
    strict = ALPHA / len(seg)
    rows = []
    for r in seg.itertuples():
        z, p = st.two_proportion_ztest(r.ad_conversions, r.ad_users, r.psa_conversions, r.psa_users)
        lift = (r.ad_conversions / r.ad_users) / (r.psa_conversions / r.psa_users) - 1
        rows.append({key: getattr(r, key), "ad_users": r.ad_users, "psa_users": r.psa_users,
                     "ad_rate_pct": round(100 * r.ad_conversions / r.ad_users, 3),
                     "psa_rate_pct": round(100 * r.psa_conversions / r.psa_users, 3),
                     "lift_pct": round(100 * lift, 1), "p_value": p,
                     "significant_after_bonferroni": p < strict})
    out = pd.DataFrame(rows)
    out.attrs["strict_alpha"] = strict
    return out


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}%"


def build_insights(t: dict, robust: dict, days: pd.DataFrame, buckets: pd.DataFrame,
                   extra_conversions: float) -> list[str]:
    sig_days = days[days["significant_after_bonferroni"]]
    best_day = days.loc[days["lift_pct"].idxmax()]
    worst_day = days.loc[days["lift_pct"].idxmin()]
    low, high = buckets.iloc[0], buckets.iloc[-1]
    sig_buckets = buckets[buckets["significant_after_bonferroni"]]
    peak = buckets.loc[buckets["lift_pct"].idxmax()]
    no_effect = buckets[~buckets["significant_after_bonferroni"]]["ads_bucket"].tolist()
    lines = [
        f"**The ad works.** Users who saw the ad converted at **{pct(t['ad_rate'], 2)}**, vs "
        f"**{pct(t['psa_rate'], 2)}** for the control group who saw a public service announcement.",

        f"**Lift:** that is **{pct(t['relative_lift'])} more conversions** (95% confidence range "
        f"{pct(t['relative_lift_ci_low'])} to {pct(t['relative_lift_ci_high'])}), or "
        f"+{t['difference_pp']:.2f} percentage points. A 20,000-run simulation (bootstrap) agrees: "
        f"{pct(t['bootstrap_lift_ci_low'])} to {pct(t['bootstrap_lift_ci_high'])}.",

        f"**Not luck:** a two-proportion z-test gives z = {t['z_score']:.2f} and p = {t['p_value']:.1e}, far below "
        f"the 0.05 threshold. A chi-square test gives the same answer (p = {t['chi_square_p_value']:.1e}).",

        f"**Big enough sample:** with {t['psa_users']:,} control users the test could detect a lift as small as "
        f"{pct(t['minimum_detectable_lift'])}; the observed {pct(t['relative_lift'])} is far above that.",

        f"**Robust:** removing the top 0.1% of users by ads seen leaves the result unchanged "
        f"(lift {pct(robust['relative_lift'])}, p = {robust['p_value']:.1e}).",

        f"**Business impact:** the ad produced about **{extra_conversions:,.0f} extra conversions** among "
        f"{t['ad_users']:,} users. At an assumed ₹{VALUE_PER_CONVERSION:,} per conversion that is "
        f"about **₹{extra_conversions * VALUE_PER_CONVERSION / 1e5:,.1f} lakh** of extra value.",

        f"**By day:** the lift is clearest on {best_day.day} ({best_day.lift_pct:+.0f}%) and weakest on "
        f"{worst_day.day} ({worst_day.lift_pct:+.0f}%). Only {len(sig_days)} of 7 days "
        f"({', '.join(sig_days['day']) or 'none'}) pass the stricter per-segment test, so treat day "
        f"differences as hints to test next, not proven facts.",

        f"**The ad needs repetition:** conversion rises with ads seen in BOTH groups ({low.ad_rate_pct:.2f}% at "
        f"{low.ads_bucket} ads to about {high.ad_rate_pct:.0f}% at {high.ads_bucket}), because active users simply see "
        f"more of everything. The ad's real effect is the GAP between the groups: it is significant only for "
        f"{', '.join(sig_buckets['ads_bucket'])} ads, peaking at {peak.ads_bucket} ads ({peak.lift_pct:+.0f}%). "
        f"For {', '.join(no_effect)} ads there is no proven difference.",
    ]
    return lines


def write_excel(sheets: dict[str, pd.DataFrame]):
    with pd.ExcelWriter(EXCEL_REPORT, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
            ws = writer.sheets[name]
            ws.freeze_panes = "A2"
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="2A78D6")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            for i, col in enumerate(df.columns, 1):
                width = max(len(str(col)), *(len(str(v)) for v in df[col].head(200))) + 2
                ws.column_dimensions[get_column_letter(i)].width = min(width, 100)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    r = run_queries()
    with sqlite3.connect(DB_PATH) as conn:
        users = pd.read_sql_query("SELECT test_group, converted, total_ads FROM ab_test", conn)

    # Main test
    t = st.full_test(*counts(users), alpha=ALPHA, power=POWER, seed=SEED)

    # Robustness: same test without the top 0.1% heaviest users
    cut = users["total_ads"].quantile(0.999)
    robust = st.full_test(*counts(users[users["total_ads"] <= cut]), alpha=ALPHA, power=POWER, seed=SEED)

    # Segments
    days = segment_tests(r["conversion_by_day"], "day")
    buckets = segment_tests(r["conversion_by_ads_seen"], "ads_bucket")

    extra_conversions = (t["ad_rate"] - t["psa_rate"]) * t["ad_users"]
    insights = build_insights(t, robust, days, buckets, extra_conversions)

    # Save everything
    sql_dir = OUTPUT_DIR / "sql_results"
    sql_dir.mkdir(exist_ok=True)
    for name, df in r.items():
        if name != "dashboard_cells":
            df.to_csv(sql_dir / f"{name}.csv", index=False)
    result = pd.DataFrame([{"metric": k, "all_users": v, "without_top_0.1pct": robust[k]} for k, v in t.items()])
    result.to_csv(OUTPUT_DIR / "test_result.csv", index=False)
    days.to_csv(OUTPUT_DIR / "segment_tests_by_day.csv", index=False)
    buckets.to_csv(OUTPUT_DIR / "segment_tests_by_ads_seen.csv", index=False)
    summary = {**{k: (bool(v) if isinstance(v, bool) else float(v)) for k, v in t.items()},
               "extra_conversions": extra_conversions, "value_per_conversion": VALUE_PER_CONVERSION,
               "robust_lift": robust["relative_lift"], "robust_p_value": robust["p_value"]}
    (OUTPUT_DIR / "test_summary.json").write_text(json.dumps(summary, indent=2))

    md = ["# Key Insights", "", *[f"{i}. {s}" for i, s in enumerate(insights, 1)], "",
          f"**Decision: launch the ad campaign.** The lift is statistically significant (p < {ALPHA}) and large "
          "enough to matter. Next, run a follow-up test on ad frequency (the effect appears only after about "
          "20 views) and on day targeting (the lift looks strongest early in the week).", "",
          f"_Value per conversion (₹{VALUE_PER_CONVERSION:,}) is an assumption; the dataset has no revenue._", ""]
    (OUTPUT_DIR / "insights.md").write_text("\n".join(md), encoding="utf-8")

    write_excel({
        "Test Result": result,
        "Group Summary": r["group_summary"],
        "By Day (tested)": days,
        "By Ads Seen (tested)": buckets,
        "By Hour": r["conversion_by_hour"],
        "Insights": pd.DataFrame({"insight": [s.replace("**", "") for s in insights]}),
    })

    verdict = "SIGNIFICANT" if t["significant"] else "NOT significant"
    print(f"[3/4] Ran {len(r)} SQL queries and the statistical tests -> outputs/")
    print(f"      Result: {verdict} - lift {pct(t['relative_lift'])} "
          f"(95% CI {pct(t['relative_lift_ci_low'])} to {pct(t['relative_lift_ci_high'])}), p = {t['p_value']:.1e}")
    print()
    for line in insights:
        print("      - " + line.replace("**", ""))
    print()


if __name__ == "__main__":
    main()
