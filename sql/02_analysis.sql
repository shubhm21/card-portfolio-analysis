-- =========================================================
-- Card Portfolio Analysis — business questions
-- Snapshot date: 2020-02-29 (latest month in the data)
-- =========================================================

-- Q01: Portfolio KPIs
SELECT
    COUNT(*)                                        AS total_cards,
    COUNT(DISTINCT client_id)                       AS clients,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT client_id), 2) AS cards_per_client,
    SUM(credit_limit)                               AS total_credit_limit,
    ROUND(AVG(credit_limit), 0)                     AS avg_credit_limit,
    ROUND(100.0 * AVG(has_chip), 1)                 AS chip_pct,
    ROUND(100.0 * AVG(flag_stale_pin), 1)           AS stale_pin_pct,
    ROUND(100.0 * AVG(flag_expired), 1)             AS expired_pct,
    SUM(card_on_dark_web)                           AS dark_web_cards
FROM fact_cards;

-- Q02: Mix by brand and card type, with share of portfolio
SELECT
    card_brand,
    card_type,
    COUNT(*)                                                    AS cards,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)          AS pct_of_cards,
    SUM(credit_limit)                                           AS total_limit,
    ROUND(AVG(credit_limit), 0)                                 AS avg_limit
FROM fact_cards
GROUP BY card_brand, card_type
ORDER BY cards DESC;

-- Q03: Credit-limit band distribution by card type
SELECT
    card_type,
    limit_band,
    COUNT(*) AS cards
FROM fact_cards
GROUP BY card_type, limit_band
ORDER BY card_type,
    CASE limit_band WHEN '$0' THEN 0 WHEN '$1-1K' THEN 1 WHEN '$1K-5K' THEN 2
        WHEN '$5K-10K' THEN 3 WHEN '$10K-20K' THEN 4 WHEN '$20K-50K' THEN 5 ELSE 6 END;

-- Q04: Security posture by brand (chip, stale PIN, risk tier)
SELECT
    card_brand,
    COUNT(*)                                            AS cards,
    ROUND(100.0 * AVG(has_chip), 1)                     AS chip_pct,
    ROUND(100.0 * AVG(flag_stale_pin), 1)               AS stale_pin_pct,
    SUM(CASE WHEN risk_tier = 'High' THEN 1 ELSE 0 END) AS high_risk_cards,
    ROUND(100.0 * AVG(CASE WHEN risk_tier = 'High' THEN 1.0 ELSE 0 END), 1) AS high_risk_pct
FROM fact_cards
GROUP BY card_brand
ORDER BY high_risk_pct DESC;

-- Q05: Expiry pipeline — cards that need reissuing
SELECT
    expiry_status,
    card_type,
    COUNT(*)             AS cards,
    SUM(credit_limit)    AS limit_at_stake
FROM fact_cards
GROUP BY expiry_status, card_type
ORDER BY expiry_status, cards DESC;

-- Q06: Accounts opened per year with running total and YoY change
WITH yearly AS (
    SELECT acct_open_year, COUNT(*) AS opened
    FROM fact_cards
    GROUP BY acct_open_year
)
SELECT
    acct_open_year,
    opened,
    SUM(opened) OVER (ORDER BY acct_open_year)                  AS running_total,
    opened - LAG(opened) OVER (ORDER BY acct_open_year)         AS yoy_change
FROM yearly
ORDER BY acct_open_year;

-- Q07: Client concentration — how many cards clients hold
SELECT
    cards            AS cards_held,
    COUNT(*)         AS clients,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_clients
FROM dim_client
GROUP BY cards
ORDER BY cards;

-- Q08: Top 10 clients by total credit limit (ranked)
SELECT *
FROM (
    SELECT
        client_id,
        cards,
        brands,
        total_credit_limit,
        max_risk_score,
        RANK() OVER (ORDER BY total_credit_limit DESC) AS limit_rank
    FROM dim_client
) ranked
WHERE limit_rank <= 10
ORDER BY limit_rank;

-- Q09: Clients with 2+ high-risk cards (outreach list)
SELECT
    c.client_id,
    COUNT(*)                                             AS high_risk_cards,
    SUM(c.flag_no_chip)                                  AS no_chip,
    SUM(c.flag_stale_pin)                                AS stale_pin,
    SUM(c.flag_expired)                                  AS expired,
    SUM(c.credit_limit)                                  AS limit_exposed
FROM fact_cards c
WHERE c.risk_tier = 'High'
GROUP BY c.client_id
HAVING COUNT(*) >= 2
ORDER BY high_risk_cards DESC, limit_exposed DESC;

-- Q10: Credit limit vs. account age bucket (do older accounts get higher limits?)
SELECT
    CASE
        WHEN account_age_years < 5  THEN '0-5 yrs'
        WHEN account_age_years < 10 THEN '5-10 yrs'
        WHEN account_age_years < 15 THEN '10-15 yrs'
        WHEN account_age_years < 20 THEN '15-20 yrs'
        ELSE '20+ yrs'
    END                          AS account_age_bucket,
    COUNT(*)                     AS cards,
    ROUND(AVG(credit_limit), 0)  AS avg_limit
FROM fact_cards
WHERE card_type <> 'Debit (Prepaid)'
GROUP BY 1
ORDER BY MIN(account_age_years);

-- Q11: Data-quality audit
SELECT 'Opened Jan-Feb 2020 (batch anomaly)' AS check_name, SUM(dq_2020_batch) AS cards FROM fact_cards
UNION ALL
SELECT 'Valid for under 12 months', SUM(dq_short_life) FROM fact_cards
UNION ALL
SELECT '$0 credit limit', SUM(CASE WHEN credit_limit = 0 THEN 1 ELSE 0 END) FROM fact_cards
UNION ALL
SELECT 'Debit cards carrying a credit limit', SUM(CASE WHEN card_type = 'Debit' AND credit_limit > 0 THEN 1 ELSE 0 END) FROM fact_cards
UNION ALL
SELECT 'Flagged on dark web', SUM(card_on_dark_web) FROM fact_cards;
