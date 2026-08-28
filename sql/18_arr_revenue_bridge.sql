-- ARR bridge is the MRR bridge × 12 (run-rate).
CREATE OR REPLACE VIEW stg.arr_revenue_bridge AS
SELECT
    d.month_start,
    COALESCE(lag(a.arr) OVER (ORDER BY d.month_start), 0)::DECIMAL(18, 4) AS beg_arr,
    COALESCE(ac.new_arr, 0)::DECIMAL(18, 4) AS new_arr,
    COALESCE(ac.expansion_arr, 0)::DECIMAL(18, 4) AS expansion_arr,
    COALESCE(ac.reactivation_arr, 0)::DECIMAL(18, 4) AS reactivation_arr,
    COALESCE(ac.contraction_arr, 0)::DECIMAL(18, 4) AS contraction_arr,
    COALESCE(ac.churn_arr, 0)::DECIMAL(18, 4) AS churn_arr,
    COALESCE(a.arr, 0)::DECIMAL(18, 4) AS end_arr,
    (
        COALESCE(lag(a.arr) OVER (ORDER BY d.month_start), 0)
        + COALESCE(ac.new_arr, 0)
        + COALESCE(ac.expansion_arr, 0)
        + COALESCE(ac.reactivation_arr, 0)
        - COALESCE(ac.contraction_arr, 0)
        - COALESCE(ac.churn_arr, 0)
    )::DECIMAL(18, 4) AS implied_end_arr
FROM stg.date_spine AS d
LEFT JOIN stg.arr AS a
    USING (month_start)
LEFT JOIN stg.arr_change AS ac
    USING (month_start);
