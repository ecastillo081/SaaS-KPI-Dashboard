create or replace view stg.active_customers as
    select
        month_start,
        count(distinct customer_id) as active_customers
    from stg.mrr_extension
    group by month_start
    order by month_start;