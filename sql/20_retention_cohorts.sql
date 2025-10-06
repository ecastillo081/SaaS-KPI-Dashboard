create or replace view stg.retention_cohorts as
    with customer_cohorts as (
        select
            customer_id,
            date_trunc('month',signup_date) as cohort_month
        from raw.customers
    ),
        active_customers as (
            select
                month_start,
                customer_id,
                price_mrr
            from stg.mrr_extension
        ),
        cohort_detail as (
            select
                month_start,
                cohort_month,
                customer_id,
                price_mrr
            from active_customers
            join customer_cohorts using(customer_id)
            where month_start >= cohort_month
        ),
        cohort_mrr as (
            select
                cohort_month,
                month_start,
                sum(price_mrr) as cohort_mrr
            from cohort_detail
            group by cohort_month, month_start
        ),
        beg_cohort_mrr as (
            select
                cohort_month,
                sum(price_mrr) as beg_cohort_mrr
            from cohort_detail
            where month_start = cohort_month
            group by cohort_month
        ),
        retention_rates as (
            select
                cohort_month,
                month_start,
                extract(year from age(month_start,cohort_month)) * 12 + extract(month from age(month_start,cohort_month)) as months_since_signup,
                cohort_mrr,
                beg_cohort_mrr,
                cohort_mrr / beg_cohort_mrr as retention_rate
            from cohort_mrr
            left join beg_cohort_mrr using(cohort_month)
        )
select
    cohort_month,
    months_since_signup,
    cohort_mrr,
    beg_cohort_mrr,
    retention_rate
from retention_rates
order by cohort_month, months_since_signup;