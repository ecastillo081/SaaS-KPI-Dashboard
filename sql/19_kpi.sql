-- Monthly executive KPI table.
-- modeled_ltv_revenue_churn is intentionally omitted; see stg.cac_ltv.
CREATE OR REPLACE VIEW stg.kpi AS
SELECT
    d.month_start,
    m.mrr,
    a.arr,
    n.nrr,
    n.grr,
    n.revenue_churn_rate,
    c.new_customers,
    c.cac_total,
    c.cac_per_customer,
    c.arpu,
    c.payback_months,
    c.active_customers
FROM stg.date_spine AS d
LEFT JOIN stg.mrr AS m
    USING (month_start)
LEFT JOIN stg.arr AS a
    USING (month_start)
LEFT JOIN stg.nrr_grr AS n
    USING (month_start)
LEFT JOIN stg.cac_ltv AS c
    USING (month_start);
