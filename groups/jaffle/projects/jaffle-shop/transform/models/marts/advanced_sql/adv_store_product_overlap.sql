-- adv_store_product_overlap.sql
-- Technique: Set Intersection via JOIN (cross-database compatible)
-- Compares product assortments across stores using relational joins
-- instead of array operations for cross-database compatibility.

with order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

-- Build distinct product set per store
store_products as (

    select distinct
        o.location_id,
        l.location_name,
        oi.product_id
    from order_items as oi
    inner join orders as o
        on oi.order_id = o.order_id
    inner join locations as l
        on o.location_id = l.location_id

),

-- Count products per store
store_product_counts as (

    select
        location_id,
        location_name,
        count(distinct product_id) as product_count
    from store_products
    group by 1, 2

),

-- Self-join to compare all pairs of stores
store_pairs as (

    select
        a.location_id as store_a_id,
        a.location_name as store_a_name,
        a.product_count as store_a_product_count,
        b.location_id as store_b_id,
        b.location_name as store_b_name,
        b.product_count as store_b_product_count
    from store_product_counts as a
    inner join store_product_counts as b
        on a.location_id < b.location_id  -- avoid duplicate pairs and self-join

),

-- Calculate intersection size using inner join on product sets
shared_products as (

    select
        a.location_id as store_a_id,
        b.location_id as store_b_id,
        count(*) as shared_product_count
    from store_products as a
    inner join store_products as b
        on a.product_id = b.product_id
       and a.location_id < b.location_id
    group by 1, 2

),

-- Combine pair info with overlap counts
store_overlap as (

    select
        sp.store_a_id,
        sp.store_a_name,
        sp.store_a_product_count,
        sp.store_b_id,
        sp.store_b_name,
        sp.store_b_product_count,
        coalesce(sh.shared_product_count, 0) as shared_product_count,
        coalesce(sh.shared_product_count, 0) > 0 as has_overlap
    from store_pairs as sp
    left join shared_products as sh
        on sp.store_a_id = sh.store_a_id
       and sp.store_b_id = sh.store_b_id

)

select
    store_a_id,
    store_a_name,
    store_a_product_count,
    store_b_id,
    store_b_name,
    store_b_product_count,
    shared_product_count,
    has_overlap,
    -- Jaccard similarity: intersection / union
    round(
        (shared_product_count::numeric /
        nullif((store_a_product_count + store_b_product_count - shared_product_count), 0)), 3
    ) as jaccard_similarity,
    -- Products unique to store A
    store_a_product_count - shared_product_count as unique_to_store_a,
    -- Products unique to store B
    store_b_product_count - shared_product_count as unique_to_store_b
from store_overlap
order by jaccard_similarity desc, store_a_id, store_b_id
