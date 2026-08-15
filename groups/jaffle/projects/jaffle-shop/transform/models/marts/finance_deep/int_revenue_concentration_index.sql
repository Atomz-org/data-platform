with

orders as (

    select * from {{ ref('stg_orders') }}

),

customer_revenue_by_store as (

    select
        location_id,
        customer_id,
        sum(order_total) as customer_revenue
    from orders
    group by 1, 2

),

store_total as (

    select
        location_id,
        sum(customer_revenue) as store_total_revenue,
        count(distinct customer_id) as customer_count
    from customer_revenue_by_store
    group by 1

),

market_share as (

    select
        crs.location_id,
        crs.customer_id,
        crs.customer_revenue,
        st.store_total_revenue,
        case
            when st.store_total_revenue > 0
                then crs.customer_revenue / st.store_total_revenue
            else 0
        end as revenue_share
    from customer_revenue_by_store as crs
    inner join store_total as st
        on crs.location_id = st.location_id

),

herfindahl as (

    select
        ms.location_id,
        st.customer_count,
        st.store_total_revenue,
        sum(ms.revenue_share * ms.revenue_share) as herfindahl_index,
        case
            when sum(ms.revenue_share * ms.revenue_share) < 0.01 then 'highly_diversified'
            when sum(ms.revenue_share * ms.revenue_share) < 0.05 then 'diversified'
            when sum(ms.revenue_share * ms.revenue_share) < 0.15 then 'moderate_concentration'
            else 'high_concentration'
        end as concentration_level
    from market_share as ms
    inner join store_total as st
        on ms.location_id = st.location_id
    group by 1, 2, 3

)

select * from herfindahl
