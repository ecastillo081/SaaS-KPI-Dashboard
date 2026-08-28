-- ARR movements are run-rate (MRR movement × 12).
CREATE OR REPLACE VIEW stg.arr_change AS
SELECT
    month_start,
    (new_mrr * 12)::DECIMAL(18, 4) AS new_arr,
    (expansion_mrr * 12)::DECIMAL(18, 4) AS expansion_arr,
    (reactivation_mrr * 12)::DECIMAL(18, 4) AS reactivation_arr,
    (contraction_mrr * 12)::DECIMAL(18, 4) AS contraction_arr,
    (churn_mrr * 12)::DECIMAL(18, 4) AS churn_arr
FROM stg.mrr_change;
