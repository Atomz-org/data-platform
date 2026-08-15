with 
o as (
    select * from {{ ref('stg_orders') }}
),

oi as (
    select * from {{ ref('stg_order_items') }}
),

monthly as (
    select
        {{ sf_date_trunc('month', "o.ordered_at") }} as order_month,
        count(distinct o.order_id) as total_orders,
        count(oi.order_item_id) as total_items,
        round(count(oi.order_item_id) * 1.0 / nullif(count(distinct o.order_id), 0), 2) as avg_basket_size
    from o
    inner join oi on o.order_id = oi.order_id
    group by 1
),
final as (
    select
        order_month,
        total_orders,
        total_items,
        avg_basket_size,
        lag(avg_basket_size) over (order by order_month) as prior_month_basket
    from monthly
)
select * from final
