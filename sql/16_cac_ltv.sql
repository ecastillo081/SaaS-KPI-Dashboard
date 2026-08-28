-- Unit economics by month.
-- CAC is assigned synthetic CAC from raw.customers, not GL marketing spend.
-- ARPU is blended snapshot MRR / active customers.
-- payback_months = CAC / (ARPU × gross_margin).
-- modeled_ltv_revenue_churn is a simplified illustration only:
--   (ARPU × GM) / monthly revenue churn, or ARPU × GM × 60 when revenue churn is 0.
-- It is not customer lifetime value from a survival model and is excluded from stg.kpi.
CREATE OR REPLACE VIEW stg.cac_ltv AS
WITH cac_per_customer AS (
    SELECT
        date_trunc('month', signup_date)::DATE AS month_start,
        COUNT(DISTINCT customer_id) AS new_customers,
        SUM(cac)::DECIMAL(18, 4) AS cac_total,
        (SUM(cac) / COUNT(DISTINCT customer_id))::DECIMAL(18, 4) AS cac_per_customer
    FROM raw.customers
    WHERE signup_date <= (SELECT as_of_date FROM stg.assumptions)
    GROUP BY 1
),
active_customers_mrr AS (
    SELECT
        month_start,
        COUNT(DISTINCT customer_id) AS active_customers,
        SUM(price_mrr)::DECIMAL(18, 4) AS total_mrr,
        (SUM(price_mrr) / COUNT(DISTINCT customer_id))::DECIMAL(18, 4) AS arpu
    FROM stg.mrr_extension
    GROUP BY month_start
)
SELECT
    d.month_start,
    c.new_customers,
    c.cac_total,
    c.cac_per_customer,
    a.arpu,
    a.active_customers,
    g.gross_margin,
    n.revenue_churn_rate,
    CASE
        WHEN a.arpu IS NULL OR a.arpu * g.gross_margin = 0 THEN NULL
        WHEN n.revenue_churn_rate IS NULL OR n.revenue_churn_rate = 0
            THEN (a.arpu * g.gross_margin * 60)::DECIMAL(18, 4)
        ELSE ((a.arpu * g.gross_margin) / n.revenue_churn_rate)::DECIMAL(18, 4)
    END AS modeled_ltv_revenue_churn,
    CASE
        WHEN c.cac_per_customer IS NULL THEN NULL
        WHEN a.arpu IS NULL OR a.arpu * g.gross_margin = 0 THEN NULL
        ELSE (c.cac_per_customer / (a.arpu * g.gross_margin))::DECIMAL(18, 4)
    END AS payback_months
FROM stg.date_spine AS d
LEFT JOIN cac_per_customer AS c
    USING (month_start)
LEFT JOIN active_customers_mrr AS a
    USING (month_start)
LEFT JOIN stg.nrr_grr AS n
    USING (month_start)
CROSS JOIN stg.assumptions AS g;
