create or replace view stg.cac_ltv as
    with cac_per_customer as (select date_trunc('month', signup_date) as month_start,
                                count(distinct customer_id)      as new_customers,
                                SUM(cac)                         as cac_total,
                                SUM(cac) / count(distinct customer_id) as cac_per_customer
                         from raw.customers
                         group by month_start
                         order by month_start),
        active_customers_mrr as (
            select
                month_start,
                count(distinct customer_id) as active_customers,
                SUM(price_mrr)                   as total_mrr,
                SUM(price_mrr) / count(distinct customer_id) as arpu
from stg.mrr_extension
group by month_start)
select
    d.month_start,
    c.new_customers,
    c.cac_total,
    c.cac_per_customer,
    arpu,
    gross_margin,
    churn_rate,
    case
        when churn_rate = 0 then (arpu * gross_margin) * 5 * 12 -- assume 5 years if no churn
            else (arpu * gross_margin) / churn_rate
        end as ltv,
    cac_per_customer / arpu * gross_margin as payback_period
from stg.date_spine as d
left join cac_per_customer as c using(month_start)
left join active_customers_mrr using(month_start)
left join stg.nrr_grr as n using(month_start)
cross join stg.assumptions
order by month_start