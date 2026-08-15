with

daily_summary as (

    select * from {{ ref('wide_daily_business_summary') }}

),

monthly as (

    select
        {{ dbt.date_trunc('month', 'summary_date') }} as summary_month,
        sum(total_revenue) as monthly_revenue,
        sum(total_orders) as monthly_orders,
        round(avg(avg_order_value), 2) as avg_order_value,
        sum(total_new_customers) as total_new_customers,
        sum(total_labor_cost) as monthly_labor_cost,
        sum(total_waste_cost) as monthly_waste_cost,
        round(sum(total_labor_cost) * 100.0 / nullif(sum(total_revenue), 0), 2) as labor_cost_pct,
        round(sum(total_waste_cost) * 100.0 / nullif(sum(total_revenue), 0), 2) as waste_cost_pct

    from daily_summary
    group by {{ dbt.date_trunc('month', 'summary_date') }}

)

select
    summary_month,
    monthly_revenue,
    monthly_orders,
    avg_order_value,
    total_new_customers,
    monthly_labor_cost,
    monthly_waste_cost,
    labor_cost_pct,
    waste_cost_pct,
    lag(monthly_revenue) over (order by summary_month) as prev_month_revenue,
    round(
        (monthly_revenue - lag(monthly_revenue) over (order by summary_month))
        * 100.0 / nullif(lag(monthly_revenue) over (order by summary_month), 0), 2
    ) as mom_revenue_growth_pct,
    lag(monthly_revenue, 12) over (order by summary_month) as yoy_month_revenue,
    round(
        (monthly_revenue - lag(monthly_revenue, 12) over (order by summary_month))
        * 100.0 / nullif(lag(monthly_revenue, 12) over (order by summary_month), 0), 2
    ) as yoy_revenue_growth_pct

from monthly
