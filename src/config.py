"""Shared settings: file paths and the test's decision rules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RAW_CSV = ROOT / "data" / "raw" / "marketing_AB.csv.gz"
CLEAN_CSV = ROOT / "data" / "processed" / "ab_test_clean.csv.gz"
DB_PATH = ROOT / "data" / "ab_test.db"

SCHEMA_SQL = ROOT / "sql" / "01_create_tables.sql"
QUERIES_SQL = ROOT / "sql" / "02_ab_queries.sql"

OUTPUT_DIR = ROOT / "outputs"
EXCEL_REPORT = OUTPUT_DIR / "ab_test_report.xlsx"
DASHBOARD_HTML = ROOT / "docs" / "index.html"
IMAGES_DIR = ROOT / "images"

TREATMENT = "ad"     # saw the real advert
CONTROL = "psa"      # saw a public service announcement instead (no advert)

# Decision rules, fixed BEFORE looking at the results
ALPHA = 0.05         # 5% significance level -> 95% confidence
POWER = 0.80         # used to work out the smallest lift the test could detect

# Business assumption (the dataset has no revenue): what one conversion is worth.
# Change it here or in the dashboard's calculator.
VALUE_PER_CONVERSION = 1000   # ₹

# Buckets for "how many ads did the user see"
AD_BUCKETS = [(1, 9, "1-9"), (10, 19, "10-19"), (20, 49, "20-49"),
              (50, 99, "50-99"), (100, 199, "100-199"), (200, 10**9, "200+")]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

SEED = 42            # for the bootstrap, so results repeat exactly
