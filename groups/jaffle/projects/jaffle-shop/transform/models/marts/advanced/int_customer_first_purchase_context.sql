with

orders as (

    select * from {{ ref('stg_orders') }}

),

order_items as (

    select * from {{ ref('stg_order_items') }}

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

date_spine as (

    select
        date_day,
        day_of_week,
        day_name,
        is_weekend
    from {{ ref('util_date_spine') }}

),

-- Identify first order per customer
first_orders as (

    select
        customer_id,
        order_id,
        location_id,
        ordered_at,
        order_total,
        subtotal,
        row_number() over (
            partition by customer_id
            order by ordered_at asc, order_id asc
        ) as rn
    from orders

),

first_order_only as (

    select * from first_orders where rn = 1

),

-- Products in first order
first_order_items as (

    select
        fo.customer_id,
        fo.order_id,
        count(distinct oi.product_id) as distinct_products,
        count(oi.order_item_id) as total_items,
        min(p.product_name) as first_product_name,
        max(p.product_type) as product_type_sample
    from first_order_only as fo
    inner join order_items as oi
        on fo.order_id = oi.order_id
    inner join products as p
        on oi.product_id = p.product_id
    group by 1, 2

),

final as (

    select
        fo.customer_id,
        fo.order_id as first_order_id,
        fo.ordered_at as first_order_date,
        fo.location_id as first_store_id,
        loc.location_name as first_store_name,
        fo.order_total as first_order_total,
        fo.subtotal as first_order_subtotal,

        -- Product context
        coalesce(foi.distinct_products, 0) as first_order_distinct_products,
        coalesce(foi.total_items, 0) as first_order_total_items,
        foi.first_product_name,

        -- Day context
        ds.day_of_week as first_order_day_of_week,
        ds.day_name as first_order_day_name,
        ds.is_weekend as first_order_is_weekend

    from first_order_only as fo
    left join locations as loc
        on fo.location_id = loc.location_id
    left join first_order_items as foi
        on fo.customer_id = foi.customer_id
    left join date_spine as ds
        on fo.ordered_at = ds.date_day

)

select * from final
