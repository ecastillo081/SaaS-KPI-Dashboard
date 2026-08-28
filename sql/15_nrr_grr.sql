-- Retention from the beginning recurring-revenue base.
-- GRR = (beg - contraction - churn) / beg. Cannot exceed 100% from expansion.
-- NRR = (beg - contraction - churn + expansion) / beg.
-- New MRR and reactivation of logos not in the beginning base are excluded.
-- revenue_churn_rate = churn_mrr / beg_mrr. This is not logo churn.
CREATE OR REPLACE VIEW stg.nrr_grr AS
WITH starting_mrr AS (
    SELECT
        month_start,
        COALESCE(lag(mrr) OVER (ORDER BY month_start), 0)::DECIMAL(18, 4) AS beg_mrr
    FROM stg.mrr
)
SELECT
    s.month_start,
    s.beg_mrr,
    mc.expansion_mrr,
    mc.reactivation_mrr,
    mc.contraction_mrr,
    mc.churn_mrr,
    CASE
        WHEN s.beg_mrr = 0 THEN NULL
        ELSE ((s.beg_mrr - mc.contraction_mrr - mc.churn_mrr) / s.beg_mrr)::DECIMAL(18, 6)
    END AS grr,
    CASE
        WHEN s.beg_mrr = 0 THEN NULL
        ELSE (
            (s.beg_mrr - mc.contraction_mrr - mc.churn_mrr + mc.expansion_mrr)
            / s.beg_mrr
        )::DECIMAL(18, 6)
    END AS nrr,
    CASE
        WHEN s.beg_mrr = 0 THEN NULL
        ELSE (mc.churn_mrr / s.beg_mrr)::DECIMAL(18, 6)
    END AS revenue_churn_rate
FROM starting_mrr AS s
LEFT JOIN stg.mrr_change AS mc
    USING (month_start);
