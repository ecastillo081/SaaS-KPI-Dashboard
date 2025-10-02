create or replace view stg.mrr as
    select
        month_start,
        sum(price_mrr) as mrr
from stg.mrr_extension
group by month_start
order by month_start