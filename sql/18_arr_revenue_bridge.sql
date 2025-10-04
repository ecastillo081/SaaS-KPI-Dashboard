create or replace view stg.arr_revenue_bridge as
    select
        month_start,
        coalesce(lag(arr) over (order by month_start), 0) as beg_arr,
        new_arr,
        expansion_arr,
        contraction_arr,
        churn_arr,
        arr as end_arr
from stg.date_spine as d
left join stg.arr as a using(month_start)
left join stg.arr_change as ac using (month_start)
order by month_start