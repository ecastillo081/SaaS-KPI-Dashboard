create or replace view arr as
    select
        month_start,
        (mrr * 12) as arr
from stg.mrr
