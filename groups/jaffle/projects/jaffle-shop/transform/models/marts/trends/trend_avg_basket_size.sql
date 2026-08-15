with

o as (
    select * from {{ ref('stg_orders') }}
),

oi as (
    select * from {{ ref('stg_order_items') }}
),

daily_baskets as (
    select
        o.ordered_at as order_date,
        count(distinct o.order_id) as order_count,
        count(oi.order_item_id) as total_items,
        round(count(oi.order_item_id) * 1.0 / nullif(count(distinct o.order_id), 0), 2) as avg_basket_size
    from o
    inner join oi on o.order_id = oi.order_id
    group by 1
),

trended as (
    select
        order_date,
        avg_basket_size,
        order_count,
        total_items,
        avg(avg_basket_size) over (order by order_date rows between 6 preceding and current row) as basket_7d_ma,
        avg(avg_basket_size) over (order by order_date rows between 27 preceding and current row) as basket_28d_ma,
        lag(avg_basket_size, 7) over (order by order_date) as basket_same_day_last_week,
        case
            when avg_basket_size > avg(avg_basket_size) over (
                order by order_date rows between 27 preceding and current row
            ) * 1.15 then 'above_trend'
            when avg_basket_size < avg(avg_basket_size) over (
                order by order_date rows between 27 preceding and current row
            ) * 0.85 then 'below_trend'
            else 'on_trend'
        end as basket_trend_status
    from daily_baskets
)

select * from trended
