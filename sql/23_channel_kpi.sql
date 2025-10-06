create or replace view stg.channel_kpi as
    with channel_mrr as (
        select
            month_start,
            acquisition_channel,
            sum(price_mrr) as ch_mrr,
            count(distinct customer_id) as ch_active_customers,
            sum(price_mrr) / count(distinct customer_id) as ch_arpu
        from stg.mrr_extension
        group by month_start, acquisition_channel
    ),
        channel_arr as (
            select
                month_start,
                acquisition_channel,
                sum(ch_mrr) * 12 as ch_arr
            from channel_mrr
            group by month_start, acquisition_channel
        ),
        new_customers_channel as (
            select
                date_trunc('month',signup_date) as month_start,
                acquisition_channel,
                count(*) as new_customers,
                sum(cac) as total_cac,
                sum(cac) / count(*) as cac_per_customer
            from raw.customers
            group by month_start, acquisition_channel
        )
select
    month_start,
    acquisition_channel,
    ch_arr,
    ch_arpu,
    coalesce(new_customers,0) as new_customers,
    coalesce(total_cac,0) as total_cac,
    cac_per_customer
from stg.date_spine
left join channel_arr using(month_start)
left join channel_mrr using(month_start, acquisition_channel)
left join new_customers_channel using(month_start, acquisition_channel)
order by month_start, acquisition_channel;