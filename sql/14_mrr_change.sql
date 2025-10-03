create or replace view stg.mrr_change as
    with monthly_events as (
        select
            date_trunc('month',event_date)::date as month_start,
            event_type,
            delta_mrr
        from raw.events
    ),
        grouped_mrr as (select month_start,
                               case
                                   when event_type in ('new') and delta_mrr > 0
                                       then delta_mrr
                                   else 0
                                   end as new_mrr,
                               case
                                   when event_type in ('upgrade', 'reactivation') and delta_mrr > 0
                                       then delta_mrr
                                   else 0
                                   end as expansion_mrr,
                               case
                                   when event_type in ('downgrade') and delta_mrr < 0
                                       then delta_mrr * -1
                                   else 0
                                   end as contraction_mrr,
                               case
                                   when event_type in ('churn') and delta_mrr < 0
                                       then delta_mrr * -1
                                   else 0
                                   end as churn_mrr
                        from monthly_events)
select
    d.month_start,
    coalesce(sum(g.new_mrr),0) as new_mrr,
    coalesce(sum(g.expansion_mrr),0) as expansion_mrr,
    coalesce(sum(g.contraction_mrr),0) as contraction_mrr,
    coalesce(sum(g.churn_mrr),0) as churn_mrr
from stg.date_spine as d
left join grouped_mrr as g
using(month_start)
group by d.month_start
order by d.month_start
