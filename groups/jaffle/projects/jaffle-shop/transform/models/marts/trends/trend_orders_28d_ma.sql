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
            rows between 27 preceding and current row
        ) as orders_28d_ma,
        sum(order_count) over (
            partition by location_id order by revenue_date
            rows between 27 preceding and current row
        ) as orders_28d_total,
        row_number() over (partition by location_id order by revenue_date desc) as recency_rank
    from daily_orders
)

select * from trended
