"""Step 4 - Build the interactive HTML dashboard (docs/index.html).

Embeds small count tables (group x day x hour x ad-count bucket) with
Plotly.js in ONE page. When a filter changes, the browser re-runs the same
z-test as src/stats_tests.py on the selected users. Works offline and on
GitHub Pages.
"""
import json
import os
import re
import sqlite3

import pandas as pd
import plotly

from config import (AD_BUCKETS, CONTROL, DASHBOARD_HTML, DAYS, DB_PATH, OUTPUT_DIR, QUERIES_SQL,
                    TREATMENT, VALUE_PER_CONVERSION)
from run_analysis import load_queries

TEMPLATE = os.path.join(os.path.dirname(__file__), "dashboard_template.html")


def dashboard_data() -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        cells = pd.read_sql_query(load_queries(QUERIES_SQL)["dashboard_cells"], conn)
    buckets = [label for _, _, label in AD_BUCKETS]
    group = {TREATMENT: 0, CONTROL: 1}
    return {
        "days": DAYS,
        "buckets": buckets,
        "valuePerConversion": VALUE_PER_CONVERSION,
        "cells": [[group[r.test_group], DAYS.index(r.most_ads_day), int(r.most_ads_hour),
                   buckets.index(r.ads_bucket), int(r.users), int(r.conversions)] for r in cells.itertuples()],
    }


def insights_html() -> tuple[str, str]:
    md = (OUTPUT_DIR / "insights.md").read_text(encoding="utf-8")
    bold = lambda s: re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    items = re.findall(r"^\d+\.\s+(.*)$", md, flags=re.MULTILINE)
    decision = re.search(r"^\*\*Decision:.*$", md, flags=re.MULTILINE).group(0)
    return "".join(f"<li>{bold(s)}</li>" for s in items), bold(decision)


def main():
    plotly_js = open(os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js"),
                     encoding="utf-8").read()
    items, decision = insights_html()
    html = open(TEMPLATE, encoding="utf-8").read()
    html = (html.replace("__DATA__", json.dumps(dashboard_data(), separators=(",", ":")))
                .replace("__INSIGHTS__", items)
                .replace("__DECISION__", decision)
                .replace("__PLOTLY_JS__", plotly_js))   # last, so its text is never searched
    DASHBOARD_HTML.parent.mkdir(exist_ok=True)
    DASHBOARD_HTML.write_text(html, encoding="utf-8")
    print("[4/4] Built interactive dashboard -> docs/index.html")


if __name__ == "__main__":
    main()
