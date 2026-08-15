with

daily_customers as (
    select
        activity_date,
        active_customers,
        new_customers,
        returning_customers
    from {{ ref('met_daily_customer_metrics') }}
),

trended as (
    select
        activity_date,
        active_customers,
        new_customers,
        returning_customers,
        round(returning_customers * 100.0 / nullif(active_customers, 0), 2) as repeat_rate_pct,
        avg(round(returning_customers * 100.0 / nullif(active_customers, 0), 2)) over (
            order by activity_date rows between 6 preceding and current row
        ) as repeat_rate_7d_ma,
        avg(round(returning_customers * 100.0 / nullif(active_customers, 0), 2)) over (
            order by activity_date rows between 27 preceding and current row
        ) as repeat_rate_28d_ma,
        case
            when round(returning_customers * 100.0 / nullif(active_customers, 0), 2) > 70 then 'strong_retention'
            when round(returning_customers * 100.0 / nullif(active_customers, 0), 2) > 50 then 'moderate_retention'
            else 'low_retention'
        end as retention_band
    from daily_customers
)

select * from trended
