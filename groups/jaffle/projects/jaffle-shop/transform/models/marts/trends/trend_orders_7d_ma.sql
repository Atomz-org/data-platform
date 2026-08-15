with

daily_orders as (
    select revenue_date, location_id, order_count
    from {{ ref('met_daily_revenue_by_store') }}
),

trended as (
    select
        revenue_date,
        location_id,
        order_count,
        avg(order_count) over (
            partition by location_id order by revenue_date
            rows between 6 preceding and current row
        ) as orders_7d_ma,
        order_count - avg(order_count) over (
            partition by location_id order by revenue_date
            rows between 6 preceding and current row
        ) as orders_deviation_7d,
        case
            when order_count > avg(order_count) over (
                partition by location_id order by revenue_date
                rows between 6 preceding and current row
            ) * 1.25 then 'high'
            when order_count < avg(order_count) over (
                partition by location_id order by revenue_date
                rows between 6 preceding and current row
            ) * 0.75 then 'low'
            else 'normal'
        end as volume_flag
    from daily_orders
)

select * from trended
