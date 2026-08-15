with 
o as (
    select * from {{ ref('orders') }}
),

l as (
    select * from {{ ref('stg_locations') }}
),

store_visits as (
    select
        o.customer_id,
        o.location_id,
        l.location_name,
        count(distinct o.order_id) as visit_count,
        sum(o.order_total) as store_spend,
        min(o.ordered_at) as first_visit_at,
        max(o.ordered_at) as last_visit_at
    from o
    inner join l
        on o.location_id = l.location_id
    group by o.customer_id, o.location_id, l.location_name
),

ranked_stores as (
    select
        customer_id,
        location_id,
        location_name,
        visit_count,
        store_spend,
        first_visit_at,
        last_visit_at,
        row_number() over (
            partition by customer_id
            order by visit_count desc, store_spend desc
        ) as store_rank,
        sum(visit_count) over (partition by customer_id) as total_visits_all_stores,
        count(location_id) over (partition by customer_id) as distinct_stores_visited
    from store_visits
)

select
    customer_id,
    location_id as preferred_store_id,
    location_name as preferred_store_name,
    visit_count as preferred_store_visits,
    store_spend as preferred_store_spend,
    first_visit_at as preferred_store_first_visit,
    last_visit_at as preferred_store_last_visit,
    round(
        (cast(visit_count as {{ dbt.type_float() }})
        / nullif(total_visits_all_stores, 0) * 100), 2
    ) as preferred_store_visit_pct,
    distinct_stores_visited
from ranked_stores
where store_rank = 1
