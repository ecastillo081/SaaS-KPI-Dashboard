create or replace view stg.nrr_grr as
    with starting_mrr as (select month_start,
                                 coalesce(lag(mrr) over (order by month_start), 0) as beg_mrr
                          from stg.mrr)
    select
        s.month_start,
        beg_mrr,
        expansion_mrr,
        contraction_mrr,
        churn_mrr,
        case
            when beg_mrr = 0 then 0
                else 1.0 - (churn_mrr / beg_mrr)
            end as grr,
        case
            when beg_mrr = 0 then 0
    else (beg_mrr - churn_mrr - contraction_mrr + expansion_mrr)/ beg_mrr
            end as nrr
    from starting_mrr as s
        left join stg.churn as c
            using(month_start)
order by s.month_start
