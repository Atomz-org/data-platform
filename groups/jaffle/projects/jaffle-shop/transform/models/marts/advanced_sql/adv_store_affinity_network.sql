-- adv_store_affinity_network.sql
-- Technique: Self-join to build a graph/network of store affinities
-- Finds pairs of stores that share customers by self-joining orders on customer_id.
-- The affinity score is the Jaccard index: shared_customers / union_customers.
-- This creates a network graph where stores are nodes and edges represent
-- customer overlap, useful for cannibalization analysis and cross-promotion.

with customer_stores as (

    -- Get distinct customer-store pairs
    select distinct
        customer_id,
        location_id
    from {{ ref('stg_orders') }}

),

-- Count total unique customers per store (needed for Jaccard denominator)
store_customer_counts as (

    select
        location_id,
        count(distinct customer_id) as total_customers
    from customer_stores
    group by 1

),

locations as (

    select
        location_id,
        location_name
    from {{ ref('stg_locations') }}

),

-- Self-join: find all store pairs that share at least one customer
-- Use store_a < store_b to avoid duplicates and self-pairs
shared_customers as (

    select
        cs1.location_id as store_a_id,
        cs2.location_id as store_b_id,
        count(distinct cs1.customer_id) as shared_customers
    from customer_stores as cs1
    inner join customer_stores as cs2
        on cs1.customer_id = cs2.customer_id
        and cs1.location_id < cs2.location_id
    group by 1, 2

),

-- Calculate affinity score using Jaccard index:
-- shared / (total_a + total_b - shared)
affinity_network as (

    select
        sc.store_a_id,
        la.location_name as store_a_name,
        sc.store_b_id,
        lb.location_name as store_b_name,
        sc.shared_customers,
        scc_a.total_customers as store_a_total_customers,
        scc_b.total_customers as store_b_total_customers,

        -- Union of customers = A + B - shared (inclusion-exclusion)
        scc_a.total_customers + scc_b.total_customers - sc.shared_customers
            as union_customers,

        -- Jaccard similarity: shared / union
        round(
            (sc.shared_customers::numeric
            / nullif(scc_a.total_customers + scc_b.total_customers - sc.shared_customers, 0)), 4
        ) as affinity_score,

        -- Overlap coefficient: shared / min(A, B)
        round(
            (sc.shared_customers::numeric
            / nullif({{ sf_least(["scc_a.total_customers", "scc_b.total_customers"]) }}, 0)), 4
        ) as overlap_coefficient

    from shared_customers as sc
    inner join store_customer_counts as scc_a
        on sc.store_a_id = scc_a.location_id
    inner join store_customer_counts as scc_b
        on sc.store_b_id = scc_b.location_id
    inner join locations as la
        on sc.store_a_id = la.location_id
    inner join locations as lb
        on sc.store_b_id = lb.location_id

)

select
    store_a_id,
    store_a_name,
    store_b_id,
    store_b_name,
    shared_customers,
    store_a_total_customers,
    store_b_total_customers,
    union_customers,
    affinity_score,
    overlap_coefficient
from affinity_network
order by affinity_score desc, shared_customers desc
