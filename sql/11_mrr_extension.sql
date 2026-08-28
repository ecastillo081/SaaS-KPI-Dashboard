-- Subscription-month grain: subscriptions active at month-end (capped at as_of_date).
-- Active if start_date <= month_end AND (end_date is null OR end_date >= month_end).
CREATE OR REPLACE VIEW stg.mrr_extension AS
WITH months AS (
    SELECT
        ds.month_start,
        LEAST(
            last_day(ds.month_start),
            (SELECT as_of_date FROM stg.assumptions)
        )::DATE AS month_end
    FROM stg.date_spine AS ds
),
active_subscriptions AS (
    SELECT
        m.month_start,
        m.month_end,
        s.subscription_id,
        s.customer_id,
        c.segment,
        c.acquisition_channel,
        s.plan,
        s.price_mrr::DECIMAL(18, 4) AS price_mrr
    FROM months AS m
    INNER JOIN raw.subscriptions AS s
        ON s.start_date <= m.month_end
        AND (s.end_date IS NULL OR s.end_date >= m.month_end)
    LEFT JOIN raw.customers AS c
        USING (customer_id)
)
SELECT
    month_start,
    month_end,
    subscription_id,
    customer_id,
    segment,
    acquisition_channel,
    plan,
    price_mrr
FROM active_subscriptions;
