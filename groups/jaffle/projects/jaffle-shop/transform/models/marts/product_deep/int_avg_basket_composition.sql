with

order_items as (

    select * from {{ ref('stg_order_items') }}

),

products as (

    select
        product_id,
        product_name,
        product_type,
        product_price
    from {{ ref('stg_products') }}

),

order_summary as (

    select
        oi.order_id,
        count(oi.order_item_id) as items_in_order,
        count(distinct oi.product_id) as distinct_products,
        count(distinct p.product_type) as distinct_categories,
        sum(p.product_price) as order_total_cost
    from order_items as oi
    inner join products as p
        on oi.product_id = p.product_id
    group by 1

),

final as (

    select
        avg(items_in_order) as avg_items_per_order,
        avg(distinct_products) as avg_distinct_products_per_order,
        avg(distinct_categories) as avg_categories_per_order,
        avg(order_total_cost) as avg_basket_value,
        min(items_in_order) as min_items_per_order,
        max(items_in_order) as max_items_per_order,
        count(case when items_in_order = 1 then 1 end) as single_item_orders,
        count(case when items_in_order between 2 and 3 then 1 end) as small_basket_orders,
        count(case when items_in_order >= 4 then 1 end) as large_basket_orders,
        count(*) as total_orders
    from order_summary

)

select * from final
