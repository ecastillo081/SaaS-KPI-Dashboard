create or replace view stg.mrr_extension as
with months as (
select
    ds.month_start,
    (ds.month_start + interval '1 month - 1 day')::date as month_end
    from stg.date_spine as ds),

active_subscriptions as (
select
    m.month_start,
    m.month_end,
    s.subscription_id,
    s.customer_id,
    segment,
    acquisition_channel,
    s.plan,
    s.price_mrr
from months as m
join raw.subscriptions as s
    on s.start_date <= m.month_end
    and (s.end_date is null or s.end_date >= m.month_end)
left join raw.customers as c
    using(customer_id)
)

select
    month_start,
    month_end,
    subscription_id,
    customer_id,
    segment,
    acquisition_channel,
    plan,
    price_mrr
from active_subscriptions
order by month_start, subscription_id
