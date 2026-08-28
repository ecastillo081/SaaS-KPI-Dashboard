-- Event-sourced MRR movements through as_of_date.
-- Expansion is in-period upgrade of existing recurring revenue only.
-- Reactivation is a separate bucket and is not expansion.
-- This golden fixture currently has no upgrade or downgrade events.
CREATE OR REPLACE VIEW stg.mrr_change AS
WITH monthly_events AS (
    SELECT
        date_trunc('month', event_date)::DATE AS month_start,
        event_type,
        delta_mrr::DECIMAL(18, 4) AS delta_mrr
    FROM raw.events
    WHERE event_date <= (SELECT as_of_date FROM stg.assumptions)
),
classified AS (
    SELECT
        month_start,
        CASE
            WHEN event_type = 'new' AND delta_mrr > 0 THEN delta_mrr
            ELSE 0
        END AS new_mrr,
        CASE
            WHEN event_type = 'upgrade' AND delta_mrr > 0 THEN delta_mrr
            ELSE 0
        END AS expansion_mrr,
        CASE
            WHEN event_type = 'reactivation' AND delta_mrr > 0 THEN delta_mrr
            ELSE 0
        END AS reactivation_mrr,
        CASE
            WHEN event_type = 'downgrade' AND delta_mrr < 0 THEN -delta_mrr
            ELSE 0
        END AS contraction_mrr,
        CASE
            WHEN event_type = 'churn' AND delta_mrr < 0 THEN -delta_mrr
            ELSE 0
        END AS churn_mrr
    FROM monthly_events
)
SELECT
    d.month_start,
    COALESCE(SUM(c.new_mrr), 0)::DECIMAL(18, 4) AS new_mrr,
    COALESCE(SUM(c.expansion_mrr), 0)::DECIMAL(18, 4) AS expansion_mrr,
    COALESCE(SUM(c.reactivation_mrr), 0)::DECIMAL(18, 4) AS reactivation_mrr,
    COALESCE(SUM(c.contraction_mrr), 0)::DECIMAL(18, 4) AS contraction_mrr,
    COALESCE(SUM(c.churn_mrr), 0)::DECIMAL(18, 4) AS churn_mrr
FROM stg.date_spine AS d
LEFT JOIN classified AS c
    USING (month_start)
GROUP BY d.month_start;
