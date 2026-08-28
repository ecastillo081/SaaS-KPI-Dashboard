-- Segment snapshot KPIs. ARR is run-rate (segment MRR × 12).
CREATE OR REPLACE VIEW stg.segment_kpi AS
WITH segment_mrr AS (
    SELECT
        month_start,
        segment,
        SUM(price_mrr)::DECIMAL(18, 4) AS segment_mrr,
        COUNT(DISTINCT customer_id) AS segment_active_customers,
        (SUM(price_mrr) / COUNT(DISTINCT customer_id))::DECIMAL(18, 4) AS segment_arpu
    FROM stg.mrr_extension
    GROUP BY month_start, segment
),
new_customers_segmented AS (
    SELECT
        date_trunc('month', signup_date)::DATE AS month_start,
        segment,
        COUNT(*) AS new_customers,
        SUM(cac)::DECIMAL(18, 4) AS total_cac,
        (SUM(cac) / COUNT(*))::DECIMAL(18, 4) AS cac_per_customer
    FROM raw.customers
    WHERE signup_date <= (SELECT as_of_date FROM stg.assumptions)
    GROUP BY 1, 2
)
SELECT
    sm.month_start,
    sm.segment,
    (sm.segment_mrr * 12)::DECIMAL(18, 4) AS segment_arr,
    sm.segment_mrr,
    sm.segment_arpu,
    sm.segment_active_customers,
    COALESCE(nc.new_customers, 0) AS new_customers,
    COALESCE(nc.total_cac, 0)::DECIMAL(18, 4) AS total_cac,
    nc.cac_per_customer
FROM segment_mrr AS sm
LEFT JOIN new_customers_segmented AS nc
    USING (month_start, segment);
