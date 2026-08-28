-- Distinct logos with at least one active subscription at month-end.
CREATE OR REPLACE VIEW stg.active_customers AS
SELECT
    month_start,
    COUNT(DISTINCT customer_id) AS active_customers
FROM stg.mrr_extension
GROUP BY month_start;
