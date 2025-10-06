create or replace view stg.segment_kpi as
       with segment_mrr as (
           select
               month_start,
               segment,
               sum(price_mrr) as segment_mrr,
               count(distinct customer_id) as segment_active_customers,
               sum(price_mrr) / count(distinct customer_id) as segment_arpu
           from stg.mrr_extension
           group by month_start, segment
       ),
           segment_arr as (
               select
                   month_start,
                   segment,
                   sum(segment_mrr) * 12 as segment_arr
                from segment_mrr
                group by month_start, segment
           ),
           new_customers_segmented as (
               select
                   date_trunc('month',signup_date) as month_start,
                     segment,
                     count(*) as new_customers,
                     sum(cac) as total_cac,
                     sum(cac) / count(*) as cac_per_customer
               from raw.customers
               group by month_start, segment
           )
select
    month_start,
    segment,
    segment_arr,
    segment_arpu,
    coalesce(new_customers,0) as new_customers,
    coalesce(total_cac,0) as total_cac,
    cac_per_customer
from stg.date_spine
left join segment_arr using(month_start)
left join segment_mrr using(month_start, segment)
left join new_customers_segmented using(month_start, segment)
order by month_start, segment;