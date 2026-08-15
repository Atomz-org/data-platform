with

daily_revenue as (
    select revenue_date, location_id, total_revenue
    from {{ ref('met_daily_revenue_by_store') }}
),

trended as (
    select
        revenue_date,
        location_id,
        total_revenue,
        avg(total_revenue) over (
            partition by location_id order by revenue_date
            rows between 27 preceding and current row
        ) as revenue_28d_ma,
        stddev(total_revenue) over (
            partition by location_id order by revenue_date
            rows between 27 preceding and current row
        ) as revenue_28d_stddev,
        case
            when total_revenue > avg(total_revenue) over (
                partition by location_id order by revenue_date
                rows between 27 preceding and current row
            ) + 2 * coalesce(nullif(stddev(total_revenue) over (
                partition by location_id order by revenue_date
                rows between 27 preceding and current row
            ), 0), 1) then 'anomaly_high'
            when total_revenue < avg(total_revenue) over (
                partition by location_id order by revenue_date
                rows between 27 preceding and current row
            ) - 2 * coalesce(nullif(stddev(total_revenue) over (
                partition by location_id order by revenue_date
                rows between 27 preceding and current row
            ), 0), 1) then 'anomaly_low'
            else 'normal'
        end as anomaly_flag
    from daily_revenue
)

select * from trended
