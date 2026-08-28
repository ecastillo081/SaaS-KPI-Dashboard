-- Month spine from the earlier of first signup / first subscription start
-- through the month containing as_of_date.
-- Does not use current_date.
CREATE OR REPLACE VIEW stg.date_spine AS
WITH bounds AS (
    SELECT
        date_trunc(
            'month',
            LEAST(
                (SELECT min(signup_date) FROM raw.customers),
                (SELECT min(start_date) FROM raw.subscriptions)
            )
        )::DATE AS min_month,
        date_trunc(
            'month',
            (SELECT as_of_date FROM stg.assumptions)
        )::DATE AS max_month
),
months AS (
    SELECT generate_series::DATE AS month_start
    FROM generate_series(
        (SELECT min_month FROM bounds),
        (SELECT max_month FROM bounds),
        INTERVAL 1 MONTH
    )
)
SELECT month_start
FROM months
ORDER BY month_start;
