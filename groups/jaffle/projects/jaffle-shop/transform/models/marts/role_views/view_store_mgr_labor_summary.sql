with

daily_labor as (
    select * from {{ ref('met_daily_labor_metrics') }}
)

select
    location_id,
    work_date,
    total_labor_hours,
    total_labor_cost,
    employee_count,
    orders_per_labor_hour,
    labor_cost_pct_of_revenue,
    round(total_labor_cost / nullif(total_labor_hours, 0), 2) as avg_hourly_cost,
    case
        when labor_cost_pct_of_revenue > 40 then 'high_labor_cost'
        when labor_cost_pct_of_revenue > 25 then 'moderate_labor_cost'
        else 'normal'
    end as labor_cost_status
from daily_labor
