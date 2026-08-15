-- adv_top_n_products_per_store.sql
-- Technique: ROW_NUMBER() window function (cross-database compatible)
-- For each store, finds the top 3 best-selling products by revenue.

with locations as (

    select * from {{ ref('stg_locations') }}

),

order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

-- Aggregate revenue per product per location
product_revenue_per_store as (

    select
        o.location_id,
        p.product_id,
        p.product_name,
        sum(p.product_price) as total_revenue,
        count(oi.order_item_id) as units_sold
    from order_items as oi
    inner join orders as o
        on oi.order_id = o.order_id
    inner join products as p
        on oi.product_id = p.product_id
    group by o.location_id, p.product_id, p.product_name

),

-- Rank products within each store
ranked_products as (

    select
        pr.location_id,
        pr.product_id,
        pr.product_name,
        pr.total_revenue,
        pr.units_sold,
        row_number() over (partition by pr.location_id order by pr.total_revenue desc) as product_rank
    from product_revenue_per_store as pr

),

top_products_per_store as (

    select
        l.location_id,
        l.location_name,
        rp.product_id,
        rp.product_name,
        rp.total_revenue,
        rp.units_sold,
        rp.product_rank
    from ranked_products as rp
    inner join locations as l
        on rp.location_id = l.location_id
    where rp.product_rank <= 3

)

select * from top_products_per_store
order by location_id, product_rank
