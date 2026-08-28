-- Acquisition-channel snapshot KPIs. ARR is run-rate (channel MRR × 12).
CREATE OR REPLACE VIEW stg.channel_kpi AS
WITH channel_mrr AS (
    SELECT
        month_start,
        acquisition_channel,
        SUM(price_mrr)::DECIMAL(18, 4) AS ch_mrr,
        COUNT(DISTINCT customer_id) AS ch_active_customers,
        (SUM(price_mrr) / COUNT(DISTINCT customer_id))::DECIMAL(18, 4) AS ch_arpu
    FROM stg.mrr_extension
    GROUP BY month_start, acquisition_channel
),
new_customers_channel AS (
    SELECT
        date_trunc('month', signup_date)::DATE AS month_start,
        acquisition_channel,
        COUNT(*) AS new_customers,
        SUM(cac)::DECIMAL(18, 4) AS total_cac,
        (SUM(cac) / COUNT(*))::DECIMAL(18, 4) AS cac_per_customer
    FROM raw.customers
    WHERE signup_date <= (SELECT as_of_date FROM stg.assumptions)
    GROUP BY 1, 2
)
SELECT
    cm.month_start,
    cm.acquisition_channel,
    (cm.ch_mrr * 12)::DECIMAL(18, 4) AS ch_arr,
    cm.ch_mrr,
    cm.ch_arpu,
    cm.ch_active_customers,
    COALESCE(nc.new_customers, 0) AS new_customers,
    COALESCE(nc.total_cac, 0)::DECIMAL(18, 4) AS total_cac,
    nc.cac_per_customer
FROM channel_mrr AS cm
LEFT JOIN new_customers_channel AS nc
    USING (month_start, acquisition_channel);
