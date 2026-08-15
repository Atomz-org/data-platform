with

order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

-- Find first and last order date per product
product_order_range as (

    select
        oi.product_id,
        min(o.ordered_at) as first_ordered_at,
        max(o.ordered_at) as last_ordered_at,
        count(distinct oi.order_id) as total_orders,
        count(oi.order_item_id) as total_units_sold

    from order_items as oi

    inner join orders as o
        on oi.order_id = o.order_id

    group by 1

),

final as (

    select
        p.product_id,
        p.product_name,
        p.product_type,
        por.first_ordered_at as active_from,
        por.last_ordered_at as last_seen_at,
        {{ sf_datediff('day', "por.first_ordered_at", "por.last_ordered_at") }} as active_days,
        por.total_orders,
        por.total_units_sold,
        case
            when {{ sf_datediff('day', "por.last_ordered_at", "current_date") }} <= 30 then true
            else false
        end as is_currently_active

    from products as p

    left join product_order_range as por
        on p.product_id = por.product_id

)

select * from final
