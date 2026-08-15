with

daily_summary as (

    select * from {{ ref('int_store_daily_summary') }}

)

select
    location_id,
    order_date,
    daily_revenue,
    order_count,
    avg_order_value,
    labor_cost,
    labor_hours,
    waste_cost,
    round(labor_cost * 100.0 / nullif(daily_revenue, 0), 2) as labor_cost_pct,
    round(waste_cost * 100.0 / nullif(daily_revenue, 0), 2) as waste_pct,
    case
        when daily_revenue > 0 and labor_cost * 100.0 / nullif(daily_revenue, 0) < 30
        then 'profitable_day'
        else 'review_needed'
    end as day_assessment

from daily_summary
