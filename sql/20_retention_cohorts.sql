-- Signup-cohort dollar retention.
-- Cohort month = customer signup month.
-- Rate = cohort MRR in month N / cohort MRR in the signup month.
-- This is not logo retention and not NRR.
-- Rates can exceed 100% when a customer's first subscription starts after
-- signup month, or when a signup-month customer later reactivates.
CREATE OR REPLACE VIEW stg.retention_cohorts AS
WITH customer_cohorts AS (
    SELECT
        customer_id,
        date_trunc('month', signup_date)::DATE AS cohort_month
    FROM raw.customers
),
active_customers AS (
    SELECT
        month_start,
        customer_id,
        price_mrr
    FROM stg.mrr_extension
),
cohort_detail AS (
    SELECT
        a.month_start,
        cc.cohort_month,
        a.customer_id,
        a.price_mrr
    FROM active_customers AS a
    INNER JOIN customer_cohorts AS cc
        USING (customer_id)
    WHERE a.month_start >= cc.cohort_month
),
cohort_mrr AS (
    SELECT
        cohort_month,
        month_start,
        SUM(price_mrr)::DECIMAL(18, 4) AS cohort_mrr,
        COUNT(DISTINCT customer_id) AS cohort_active_customers
    FROM cohort_detail
    GROUP BY cohort_month, month_start
),
beg_cohort_mrr AS (
    SELECT
        cohort_month,
        SUM(price_mrr)::DECIMAL(18, 4) AS beg_cohort_mrr,
        COUNT(DISTINCT customer_id) AS beg_cohort_customers
    FROM cohort_detail
    WHERE month_start = cohort_month
    GROUP BY cohort_month
)
SELECT
    cm.cohort_month,
    date_diff('month', cm.cohort_month, cm.month_start) AS months_since_signup,
    cm.month_start,
    cm.cohort_mrr,
    b.beg_cohort_mrr,
    cm.cohort_active_customers,
    b.beg_cohort_customers,
    CASE
        WHEN b.beg_cohort_mrr IS NULL OR b.beg_cohort_mrr = 0 THEN NULL
        ELSE (cm.cohort_mrr / b.beg_cohort_mrr)::DECIMAL(18, 6)
    END AS signup_cohort_mrr_retention_rate
FROM cohort_mrr AS cm
LEFT JOIN beg_cohort_mrr AS b
    USING (cohort_month);
