"""Step 2 - Load the clean data into a SQL database (SQLite, built into Python)."""
import sqlite3

import pandas as pd

from config import CLEAN_CSV, DB_PATH, SCHEMA_SQL


def main():
    df = pd.read_csv(CLEAN_CSV)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA_SQL.read_text())
        df.to_sql("ab_test", conn, if_exists="append", index=False)
        n = conn.execute("SELECT COUNT(*) FROM ab_test").fetchone()[0]
    print(f"[2/4] Loaded SQLite database: ab_test table, {n:,} users")


if __name__ == "__main__":
    main()
