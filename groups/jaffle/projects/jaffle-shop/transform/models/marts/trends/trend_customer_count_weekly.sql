with

base as (
    select
        {{ sf_date_trunc('week', "activity_date") }} as activity_week,
        sum(active_customers) as active_customers,
        sum(new_customers) as new_customers
    from {{ ref('met_daily_customer_metrics') }}
    group by 1
),

trended as (
    select
        activity_week,
        active_customers,
        new_customers,
        active_customers - new_customers as returning_customers,
        avg(active_customers) over (order by activity_week rows between 3 preceding and current row) as customers_4w_ma,
        avg(new_customers) over (order by activity_week rows between 3 preceding and current row) as new_customers_4w_ma,
        lag(active_customers) over (order by activity_week) as prev_week_customers,
        round(((active_customers - lag(active_customers) over (order by activity_week))) * 100.0
            / nullif(lag(active_customers) over (order by activity_week), 0), 2) as wow_growth_pct
    from base
)

select * from trended
