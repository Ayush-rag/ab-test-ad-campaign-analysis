-- ============================================================
-- One table: one row per user in the experiment.
-- Written for SQLite; works in MySQL 8 unchanged.
-- ============================================================

DROP TABLE IF EXISTS ab_test;

CREATE TABLE ab_test (
    user_id        INTEGER     PRIMARY KEY,   -- each user appears once
    test_group     VARCHAR(3)  NOT NULL,      -- 'ad' (saw the advert) or 'psa' (control)
    converted      INTEGER     NOT NULL,      -- 1 = bought, 0 = did not
    total_ads      INTEGER     NOT NULL,      -- how many ads the user saw
    most_ads_day   VARCHAR(9)  NOT NULL,      -- day the user saw the most ads
    most_ads_hour  INTEGER     NOT NULL,      -- hour (0-23) the user saw the most ads
    ads_bucket     VARCHAR(7)  NOT NULL,      -- total_ads grouped: 1-9, 10-19, ... 200+
    CHECK (test_group IN ('ad', 'psa')),
    CHECK (converted IN (0, 1)),
    CHECK (most_ads_hour BETWEEN 0 AND 23)
);

CREATE INDEX idx_ab_group ON ab_test (test_group);
