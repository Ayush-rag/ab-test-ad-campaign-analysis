"""Step 1 - Check and prepare the A/B test data.

Before trusting any test result, the data must pass basic checks: one row
per user, no missing values, only the two expected groups, valid numbers.
Each check is logged with how many rows failed it.

Works with both the tidy copy in data/raw and the original Kaggle file
(which has an extra index column, column names with spaces and True/False
in `converted`).
"""
import pandas as pd

from config import AD_BUCKETS, CLEAN_CSV, CONTROL, DAYS, OUTPUT_DIR, RAW_CSV, TREATMENT


def bucket(n: int) -> str:
    for low, high, label in AD_BUCKETS:
        if low <= n <= high:
            return label
    raise ValueError(n)


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    log = [("Rows in raw file", len(raw))]
    df = raw.copy()

    # 0. Standardise columns: 'test group' -> 'test_group'; drop a leftover index column
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.drop(columns=[c for c in df.columns if c.startswith("unnamed")])
    df["converted"] = df["converted"].astype(str).str.lower().map(
        {"true": 1, "false": 0, "1": 1, "0": 0})

    # 1. Missing values
    missing = df.isna().any(axis=1)
    log.append(("Rows with a missing value (removed)", int(missing.sum())))
    df = df[~missing]

    # 2. A user must appear only once, or they could be in both groups
    dupes = df["user_id"].duplicated(keep=False)
    log.append(("Rows with a repeated user_id (removed)", int(dupes.sum())))
    df = df[~dupes]

    # 3. Only the two expected groups
    bad_group = ~df["test_group"].isin([TREATMENT, CONTROL])
    log.append(("Rows with an unknown test group (removed)", int(bad_group.sum())))
    df = df[~bad_group]

    # 4. Valid values
    bad_values = (~df["most_ads_day"].isin(DAYS) | ~df["most_ads_hour"].between(0, 23)
                  | (df["total_ads"] < 1))
    log.append(("Rows with an invalid day, hour or ad count (removed)", int(bad_values.sum())))
    df = df[~bad_values]

    # 5. Extreme ad counts: kept (they are real users), but counted, and the
    #    analysis checks the result still holds without them
    extreme = df["total_ads"] > df["total_ads"].quantile(0.999)
    log.append(("Users who saw an extreme number of ads, top 0.1% (kept, re-tested without them)",
                int(extreme.sum())))

    # 6. New column: ad-count bucket, for segment analysis
    df["ads_bucket"] = df["total_ads"].map(bucket)
    df = df.astype({"converted": int, "total_ads": int, "most_ads_hour": int})

    log.append(("Rows in clean dataset", len(df)))
    return df.reset_index(drop=True), pd.DataFrame(log, columns=["step", "rows"])


def main():
    df, log = clean(pd.read_csv(RAW_CSV))
    CLEAN_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    df.to_csv(CLEAN_CSV, index=False)
    log.to_csv(OUTPUT_DIR / "cleaning_log.csv", index=False)
    print("[1/4] Checked and cleaned the data:")
    for step, rows in log.itertuples(index=False):
        print(f"      {step:<82} {rows:>8,}")


if __name__ == "__main__":
    main()
