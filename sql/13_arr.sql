create or replace view stg.arr as
    select
        month_start,
        (mrr * 12) as arr
from stg.mrr
