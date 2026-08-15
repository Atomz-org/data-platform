with

daily_summary as (

    select * from {{ ref('wide_daily_business_summary') }}

)

select
    {{ dbt.date_trunc('week', 'summary_date') }} as summary_week,
    sum(total_revenue) as weekly_revenue,
    sum(total_orders) as weekly_orders,
    round(avg(avg_order_value), 2) as avg_order_value,
    sum(total_active_customers) as total_active_customers,
    sum(total_new_customers) as total_new_customers,
    sum(total_labor_cost) as weekly_labor_cost,
    sum(total_labor_hours) as weekly_labor_hours,
    sum(total_waste_cost) as weekly_waste_cost,
    sum(total_waste_events) as weekly_waste_events,
    round(sum(total_labor_cost) * 100.0 / nullif(sum(total_revenue), 0), 2) as labor_cost_pct,
    round(sum(total_waste_cost) * 100.0 / nullif(sum(total_revenue), 0), 2) as waste_cost_pct,
    count(distinct summary_date) as days_in_week

from daily_summary
group by {{ dbt.date_trunc('week', 'summary_date') }}
