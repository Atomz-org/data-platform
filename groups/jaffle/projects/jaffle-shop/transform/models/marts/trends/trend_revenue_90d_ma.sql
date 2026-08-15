with

daily_revenue as (
    select revenue_date, location_id, total_revenue
    from {{ ref('met_daily_revenue_by_store') }}
),

with_moving_avg as (
    select
        revenue_date,
        location_id,
        total_revenue,
        avg(total_revenue) over (
            partition by location_id order by revenue_date
            rows between 89 preceding and current row
        ) as revenue_90d_ma,
        min(total_revenue) over (
            partition by location_id order by revenue_date
            rows between 89 preceding and current row
        ) as revenue_90d_min,
        max(total_revenue) over (
            partition by location_id order by revenue_date
            rows between 89 preceding and current row
        ) as revenue_90d_max
    from daily_revenue
),

trended as (
    select
        revenue_date,
        location_id,
        total_revenue,
        revenue_90d_ma,
        revenue_90d_min,
        revenue_90d_max,
        case
            when revenue_90d_ma > lag(revenue_90d_ma, 30) over (
                partition by location_id order by revenue_date
            )
            then 'upward'
            else 'downward_or_flat'
        end as long_term_trend
    from with_moving_avg
)

select * from trended
