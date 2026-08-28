-- Month-end snapshot MRR from active subscriptions.
CREATE OR REPLACE VIEW stg.mrr AS
SELECT
    month_start,
    SUM(price_mrr)::DECIMAL(18, 4) AS mrr
FROM stg.mrr_extension
GROUP BY month_start;
