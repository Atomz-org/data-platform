with

monthly_customers as (
    select
        month_start,
        tracked_active_customers,
        new_customers
    from {{ ref('met_monthly_customer_metrics') }}
),

trended as (
    select
        month_start,
        tracked_active_customers,
        new_customers,
        avg(tracked_active_customers) over (order by month_start rows between 2 preceding and current row) as customers_3m_ma,
        lag(tracked_active_customers) over (order by month_start) as prev_month_customers,
        round((tracked_active_customers - lag(tracked_active_customers) over (order by month_start)) * 100.0
            / nullif(lag(tracked_active_customers) over (order by month_start), 0), 2) as mom_growth_pct,
        case
            when tracked_active_customers > lag(tracked_active_customers, 3) over (order by month_start) then 'growing'
            when tracked_active_customers < lag(tracked_active_customers, 3) over (order by month_start) then 'shrinking'
            else 'stable'
        end as quarterly_trend
    from monthly_customers
)

select * from trended
