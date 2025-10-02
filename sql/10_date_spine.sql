create or replace view stg.date_spine as
with bounds as (
select date_trunc('month', LEAST(
    (select min(signup_date) from raw.customers),
    (select min(start_date) from raw.subscriptions))) as min_month,
    date_trunc('month', current_date) + interval '1 month - 1 day' as max_month),

    months as (select generate_series((select min_month from bounds),
                                      (select max_month from bounds),
                                      interval '1 month')::date as month_start)
select month_start
from months
order by month_start;