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
        product_type,
        product_price
    from {{ ref('stg_products') }}
),

category_by_store as (
    select
        p.product_type as category,
        o.location_id,
        sum(p.product_price) as category_revenue,
        count(oi.order_item_id) as category_quantity
    from order_items as oi
    inner join orders as o on oi.order_id = o.order_id
    inner join products as p on oi.product_id = p.product_id
    group by 1, 2
),

store_total as (
    select
        location_id,
        sum(category_revenue) as store_total_revenue
    from category_by_store
    group by 1
),

final as (
    select
        cbs.category,
        cbs.location_id,
        cbs.category_revenue,
        cbs.category_quantity,
        st.store_total_revenue,
        case
            when st.store_total_revenue > 0
                then round(cast(cbs.category_revenue * 100.0 / st.store_total_revenue as {{ dbt.type_float() }}), 2)
            else 0
        end as revenue_share_pct
    from category_by_store as cbs
    inner join store_total as st on cbs.location_id = st.location_id
)

select * from final
