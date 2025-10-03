create or replace view stg.arr_change as
select
    month_start,
    new_mrr * 12 as new_arr,
    expansion_mrr * 12 as expansion_arr,
    contraction_mrr * 12 as contraction_arr,
    churn_mrr * 12 as churn_arr
    from stg.mrr_change