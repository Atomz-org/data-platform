with

orders as (

    select
        order_id,
        location_id,
        ordered_at
    from {{ ref('stg_orders') }}

),

order_items as (

    select
        order_id,
        product_id,
        1 as quantity
    from {{ ref('stg_order_items') }}

),

inventory_at_order as (

    select
        product_id,
        location_id,
        current_quantity
    from {{ ref('int_inventory_current_level') }}

),

order_fulfillment as (

    select
        o.order_id,
        o.location_id,
        {{ dbt.date_trunc('month', 'o.ordered_at') }} as order_month,
        count(oi.product_id) as total_line_items,
        sum(case
            when coalesce(inv.current_quantity, 0) >= oi.quantity then 1
            else 0
        end) as fillable_line_items
    from orders as o
    inner join order_items as oi on o.order_id = oi.order_id
    left join inventory_at_order as inv
        on oi.product_id = inv.product_id
        and o.location_id = inv.location_id
    group by 1, 2, 3

),

final as (

    select
        order_month,
        location_id,
        count(*) as total_orders,
        sum(case when fillable_line_items = total_line_items then 1 else 0 end) as fully_filled_orders,
        case
            when count(*) > 0
            then cast(sum(case when fillable_line_items = total_line_items then 1 else 0 end)
                as {{ dbt.type_float() }}) / count(*) * 100
            else 0
        end as order_fill_rate_pct,
        avg(cast(fillable_line_items as {{ dbt.type_float() }}) / nullif(total_line_items, 0)) * 100
            as avg_line_fill_rate_pct
    from order_fulfillment
    group by 1, 2

)

select * from final
