-- ============================================================
-- A/B test queries. Each starts with "-- name: <name>" so Python
-- can run them one by one and save the results.
--
--   conversion rate = conversions / users
--   lift            = (ad rate - psa rate) / psa rate
-- The significance tests themselves are in src/stats_tests.py.
-- ============================================================


-- name: group_summary
-- The core result: users and conversions in each group
SELECT
    test_group,
    COUNT(*)                                             AS users,
    SUM(converted)                                       AS conversions,
    ROUND(100.0 * AVG(converted), 3)                     AS conversion_rate_pct,
    ROUND(AVG(total_ads), 1)                             AS avg_ads_seen,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)   AS share_of_users_pct
FROM ab_test
GROUP BY test_group
ORDER BY test_group;


-- name: conversion_by_day
-- Does the ad work better on some days? (day = when the user saw the most ads)
WITH g AS (
    SELECT
        most_ads_day                                              AS day,
        SUM(CASE WHEN test_group = 'ad'  THEN 1 ELSE 0 END)       AS ad_users,
        SUM(CASE WHEN test_group = 'ad'  THEN converted ELSE 0 END) AS ad_conversions,
        SUM(CASE WHEN test_group = 'psa' THEN 1 ELSE 0 END)       AS psa_users,
        SUM(CASE WHEN test_group = 'psa' THEN converted ELSE 0 END) AS psa_conversions
    FROM ab_test
    GROUP BY most_ads_day
)
SELECT
    day, ad_users, ad_conversions, psa_users, psa_conversions,
    ROUND(100.0 * ad_conversions / ad_users, 3)                   AS ad_rate_pct,
    ROUND(100.0 * psa_conversions / psa_users, 3)                 AS psa_rate_pct,
    ROUND(100.0 * (1.0 * ad_conversions / ad_users - 1.0 * psa_conversions / psa_users)
          / (1.0 * psa_conversions / psa_users), 1)               AS lift_pct
FROM g
ORDER BY CASE day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
                  WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END;


-- name: conversion_by_hour
-- Does the ad work better at some hours? (hour = when the user saw the most ads)
WITH g AS (
    SELECT
        most_ads_hour                                             AS hour,
        SUM(CASE WHEN test_group = 'ad'  THEN 1 ELSE 0 END)       AS ad_users,
        SUM(CASE WHEN test_group = 'ad'  THEN converted ELSE 0 END) AS ad_conversions,
        SUM(CASE WHEN test_group = 'psa' THEN 1 ELSE 0 END)       AS psa_users,
        SUM(CASE WHEN test_group = 'psa' THEN converted ELSE 0 END) AS psa_conversions
    FROM ab_test
    GROUP BY most_ads_hour
)
SELECT
    hour, ad_users, ad_conversions, psa_users, psa_conversions,
    ROUND(100.0 * ad_conversions / ad_users, 3)                   AS ad_rate_pct,
    ROUND(100.0 * psa_conversions / NULLIF(psa_users, 0), 3)      AS psa_rate_pct
FROM g
ORDER BY hour;


-- name: conversion_by_ads_seen
-- How does conversion change with the number of ads a user saw?
WITH g AS (
    SELECT
        ads_bucket,
        MIN(total_ads)                                            AS min_ads,
        SUM(CASE WHEN test_group = 'ad'  THEN 1 ELSE 0 END)       AS ad_users,
        SUM(CASE WHEN test_group = 'ad'  THEN converted ELSE 0 END) AS ad_conversions,
        SUM(CASE WHEN test_group = 'psa' THEN 1 ELSE 0 END)       AS psa_users,
        SUM(CASE WHEN test_group = 'psa' THEN converted ELSE 0 END) AS psa_conversions
    FROM ab_test
    GROUP BY ads_bucket
)
SELECT
    ads_bucket, ad_users, ad_conversions, psa_users, psa_conversions,
    ROUND(100.0 * ad_conversions / ad_users, 3)                   AS ad_rate_pct,
    ROUND(100.0 * psa_conversions / NULLIF(psa_users, 0), 3)      AS psa_rate_pct
FROM g
ORDER BY min_ads;


-- name: dashboard_cells
-- Smallest building blocks for the dashboard's filters:
-- users and conversions for every group x day x hour x ad-count bucket
SELECT
    test_group, most_ads_day, most_ads_hour, ads_bucket,
    COUNT(*)        AS users,
    SUM(converted)  AS conversions
FROM ab_test
GROUP BY test_group, most_ads_day, most_ads_hour, ads_bucket;
