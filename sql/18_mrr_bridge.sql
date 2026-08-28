-- Recurring-revenue bridge at MRR grain.
-- Identity: beg + new + expansion + reactivation - contraction - churn = end.
CREATE OR REPLACE VIEW stg.mrr_bridge AS
SELECT
    d.month_start,
    COALESCE(lag(m.mrr) OVER (ORDER BY d.month_start), 0)::DECIMAL(18, 4) AS beg_mrr,
    COALESCE(mc.new_mrr, 0)::DECIMAL(18, 4) AS new_mrr,
    COALESCE(mc.expansion_mrr, 0)::DECIMAL(18, 4) AS expansion_mrr,
    COALESCE(mc.reactivation_mrr, 0)::DECIMAL(18, 4) AS reactivation_mrr,
    COALESCE(mc.contraction_mrr, 0)::DECIMAL(18, 4) AS contraction_mrr,
    COALESCE(mc.churn_mrr, 0)::DECIMAL(18, 4) AS churn_mrr,
    COALESCE(m.mrr, 0)::DECIMAL(18, 4) AS end_mrr,
    (
        COALESCE(lag(m.mrr) OVER (ORDER BY d.month_start), 0)
        + COALESCE(mc.new_mrr, 0)
        + COALESCE(mc.expansion_mrr, 0)
        + COALESCE(mc.reactivation_mrr, 0)
        - COALESCE(mc.contraction_mrr, 0)
        - COALESCE(mc.churn_mrr, 0)
    )::DECIMAL(18, 4) AS implied_end_mrr
FROM stg.date_spine AS d
LEFT JOIN stg.mrr AS m
    USING (month_start)
LEFT JOIN stg.mrr_change AS mc
    USING (month_start);
