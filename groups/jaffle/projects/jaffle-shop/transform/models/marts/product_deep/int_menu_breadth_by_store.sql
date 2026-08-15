with

order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders as (

    select
        order_id,
        location_id
    from {{ ref('stg_orders') }}

),

locations as (

    select
        location_id,
        location_name
    from {{ ref('stg_locations') }}

),

final as (

    select
        o.location_id,
        l.location_name,
        count(distinct oi.product_id) as distinct_products_sold,
        count(distinct oi.order_item_id) as total_items_sold,
        count(distinct o.order_id) as total_orders,
        case
            when count(distinct o.order_id) > 0
                then round(cast(count(distinct oi.product_id) * 1.0 / count(distinct o.order_id) as {{ dbt.type_float() }}), 2)
            else 0
        end as product_diversity_ratio
    from order_items as oi
    inner join orders as o
        on oi.order_id = o.order_id
    inner join locations as l
        on o.location_id = l.location_id
    group by 1, 2

)

select * from final
