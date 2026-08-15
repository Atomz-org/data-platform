with

order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select
        product_id,
        product_name,
        product_type
    from {{ ref('stg_products') }}
),

locations as (
    select
        location_id,
        location_name
    from {{ ref('stg_locations') }}
),

product_store_sales as (
    select
        oi.product_id,
        o.location_id,
        count(oi.order_item_id) as total_units_sold,
        count(distinct oi.order_id) as total_orders,
        min(o.ordered_at) as first_sold_date,
        max(o.ordered_at) as last_sold_date
    from order_items as oi
    inner join orders as o on oi.order_id = o.order_id
    group by oi.product_id, o.location_id
),

final as (
    select
        pss.product_id,
        p.product_name,
        p.product_type,
        pss.location_id,
        l.location_name,
        pss.total_units_sold,
        pss.total_orders,
        pss.first_sold_date,
        pss.last_sold_date,
        case
            when pss.first_sold_date is not null and pss.last_sold_date is not null
                and {{ dbt.datediff('pss.first_sold_date', 'pss.last_sold_date', 'day') }} > 0
                then round(cast(
                    pss.total_units_sold * 1.0
                    / {{ dbt.datediff('pss.first_sold_date', 'pss.last_sold_date', 'day') }}
                as {{ dbt.type_float() }}), 2)
            else pss.total_units_sold
        end as daily_sales_velocity,
        case
            when pss.total_units_sold > 100 then 'fast_mover'
            when pss.total_units_sold > 30 then 'moderate_mover'
            else 'slow_mover'
        end as velocity_tier
    from product_store_sales as pss
    left join locations as l on pss.location_id = l.location_id
    left join products as p on pss.product_id = p.product_id
)

select * from final
