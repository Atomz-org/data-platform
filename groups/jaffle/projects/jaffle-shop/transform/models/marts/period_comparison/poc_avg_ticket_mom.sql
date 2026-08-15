with

monthly_aov as (
    select
        month_start,
        location_id,
        monthly_revenue,
        monthly_orders,
        round(monthly_revenue * 1.0 / nullif(monthly_orders, 0), 2) as avg_ticket
    from {{ ref('met_monthly_revenue_by_store') }}
),

compared as (
    select
        month_start,
        location_id,
        avg_ticket as current_avg_ticket,
        lag(avg_ticket) over (partition by location_id order by month_start) as prior_month_avg_ticket,
        round((avg_ticket - lag(avg_ticket) over (partition by location_id order by month_start)) * 100.0
            / nullif(lag(avg_ticket) over (partition by location_id order by month_start), 0), 2) as ticket_mom_pct
    from monthly_aov
)

select * from compared
