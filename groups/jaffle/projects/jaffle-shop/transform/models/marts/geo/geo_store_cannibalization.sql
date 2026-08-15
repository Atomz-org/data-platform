with

orders as (

    select * from {{ ref('stg_orders') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

customer_stores as (

    select
        customer_id,
        location_id,
        count(*) as order_count

    from orders
    where customer_id is not null
    group by customer_id, location_id

),

store_pairs as (

    select
        a.location_id as store_a_id,
        b.location_id as store_b_id,
        count(distinct a.customer_id) as shared_customers,
        sum(a.order_count) as store_a_orders_from_shared,
        sum(b.order_count) as store_b_orders_from_shared

    from customer_stores a
    inner join customer_stores b
        on a.customer_id = b.customer_id
        and a.location_id < b.location_id
    group by a.location_id, b.location_id

),

store_totals as (

    select
        location_id,
        count(distinct customer_id) as total_customers

    from customer_stores
    group by location_id

)

select
    sp.store_a_id,
    la.location_name as store_a_name,
    sp.store_b_id,
    lb.location_name as store_b_name,
    sp.shared_customers,
    ta.total_customers as store_a_total_customers,
    tb.total_customers as store_b_total_customers,
    round(sp.shared_customers * 100.0 / nullif(ta.total_customers, 0), 2) as store_a_overlap_pct,
    round(sp.shared_customers * 100.0 / nullif(tb.total_customers, 0), 2) as store_b_overlap_pct,
    case
        when sp.shared_customers * 100.0 / nullif({{ sf_least(["ta.total_customers", "tb.total_customers"]) }}, 0) > 30
        then 'high_cannibalization'
        when sp.shared_customers * 100.0 / nullif({{ sf_least(["ta.total_customers", "tb.total_customers"]) }}, 0) > 15
        then 'moderate_cannibalization'
        else 'low_cannibalization'
    end as cannibalization_risk

from store_pairs sp
left join locations la on sp.store_a_id = la.location_id
left join locations lb on sp.store_b_id = lb.location_id
left join store_totals ta on sp.store_a_id = ta.location_id
left join store_totals tb on sp.store_b_id = tb.location_id
