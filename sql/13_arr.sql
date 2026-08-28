-- Run-rate ARR = snapshot MRR × 12. Not recognized revenue.
CREATE OR REPLACE VIEW stg.arr AS
SELECT
    month_start,
    (mrr * 12)::DECIMAL(18, 4) AS arr
FROM stg.mrr;
