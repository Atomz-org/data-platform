with

daily_metrics as (
    select
        activity_date,
        active_customers as total_active,
        new_customers
    from {{ ref('met_daily_customer_metrics') }}
),

trended as (
    select
        activity_date,
        total_active,
        new_customers,
        round(new_customers * 100.0 / nullif(total_active, 0), 2) as new_customer_rate_pct,
        avg(new_customers) over (order by activity_date rows between 6 preceding and current row) as new_cust_7d_ma,
        avg(new_customers) over (order by activity_date rows between 27 preceding and current row) as new_cust_28d_ma,
        sum(new_customers) over (order by activity_date rows between 6 preceding and current row) as new_cust_7d_total,
        case
            when avg(new_customers) over (order by activity_date rows between 6 preceding and current row)
                > avg(new_customers) over (order by activity_date rows between 27 preceding and current row)
            then 'accelerating'
            else 'decelerating'
        end as acquisition_momentum
    from daily_metrics
)

select * from trended
