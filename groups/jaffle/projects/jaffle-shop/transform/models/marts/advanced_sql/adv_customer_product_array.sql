-- adv_customer_product_array.sql
-- Technique: Array Operations
-- Aggregates each customer's purchase history into arrays.
-- array_agg with DISTINCT and ORDER BY creates a sorted, deduplicated product list.

with order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

-- Deduplicated products per customer (needed for Snowflake array_agg which
-- does not support DISTINCT inside aggregate + WITHIN GROUP)
customer_products_deduped as (

    select distinct
        c.customer_id,
        c.customer_name,
        p.product_id,
        p.product_name,
        p.product_type
    from order_items as oi
    inner join orders as o
        on oi.order_id = o.order_id
    inner join products as p
        on oi.product_id = p.product_id
    inner join customers as c
        on o.customer_id = c.customer_id

),

-- Aggregate counts from the raw (non-deduped) data
customer_order_counts as (

    select
        c.customer_id,
        count(oi.order_item_id) as total_items_purchased,
        count(distinct o.order_id) as total_orders
    from order_items as oi
    inner join orders as o
        on oi.order_id = o.order_id
    inner join customers as c
        on o.customer_id = c.customer_id
    group by 1

),

-- Build arrays of products per customer from deduplicated data
customer_product_arrays as (

    select
        cpd.customer_id,
        cpd.customer_name,

        {% if target.type == 'snowflake' %}
        array_agg(cpd.product_id) within group (order by cpd.product_id) as products_purchased,
        array_agg(cpd.product_name) within group (order by cpd.product_name) as product_names_purchased,
        array_agg(cpd.product_type) within group (order by cpd.product_type) as product_types_purchased,
        {% else %}
        array_agg(cpd.product_id order by cpd.product_id) as products_purchased,
        array_agg(cpd.product_name order by cpd.product_name) as product_names_purchased,
        array_agg(cpd.product_type order by cpd.product_type) as product_types_purchased,
        {% endif %}

        count(cpd.product_id) as unique_product_count

    from customer_products_deduped as cpd
    group by 1, 2

)

select
    cpa.customer_id,
    cpa.customer_name,
    cpa.products_purchased,
    cpa.product_names_purchased,
    cpa.product_types_purchased,
    cpa.unique_product_count,
    coc.total_items_purchased,
    coc.total_orders,
    -- Average items per order
    round(coc.total_items_purchased::numeric / nullif(coc.total_orders, 0), 1) as avg_items_per_order,
    -- Product diversity ratio: unique products / total items
    round(cpa.unique_product_count::numeric / nullif(coc.total_items_purchased, 0), 2) as product_diversity_ratio
from customer_product_arrays as cpa
inner join customer_order_counts as coc
    on cpa.customer_id = coc.customer_id
order by cpa.unique_product_count desc, cpa.customer_id
