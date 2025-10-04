create or replace view stg.kpi as
    select
        month_start,
        arr,
        nrr,
        grr,
        new_customers,
        cac_total,
        cac_per_customer,
        arpu,
        ltv,
        payback_period
from stg.date_spine as d
left join stg.arr as a using(month_start)
left join stg.nrr_grr as n using(month_start)
left join stg.cac_ltv as c using(month_start)
order by month_start;