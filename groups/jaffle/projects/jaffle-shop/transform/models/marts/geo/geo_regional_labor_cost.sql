with

labor_metrics as (

    select * from {{ ref('met_monthly_labor_metrics') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

)

select
    lm.location_id,
    l.location_name as store_name,
    lm.month_start,
    lm.monthly_labor_cost,
    lm.monthly_labor_hours,
    round(lm.monthly_labor_cost / nullif(lm.monthly_labor_hours, 0), 2) as cost_per_hour,
    round(
        (avg(lm.monthly_labor_cost / nullif(lm.monthly_labor_hours, 0))
            over (partition by lm.month_start)), 2
    ) as fleet_avg_cost_per_hour,
    round(
        (lm.monthly_labor_cost / nullif(lm.monthly_labor_hours, 0)
        - avg(lm.monthly_labor_cost / nullif(lm.monthly_labor_hours, 0))
            over (partition by lm.month_start)), 2
    ) as cost_per_hour_vs_fleet

from labor_metrics lm
left join locations l on lm.location_id = l.location_id
