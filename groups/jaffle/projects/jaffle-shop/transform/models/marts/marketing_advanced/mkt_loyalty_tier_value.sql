with

members as (

    select
        customer_id,
        current_tier_name
    from {{ ref('dim_loyalty_members') }}

),

customer_orders as (

    select
        customer_id,
        count(order_id) as order_count,
        sum(order_total) as total_spend,
        avg(order_total) as avg_order_value
    from {{ ref('stg_orders') }}
    group by 1

),

tier_summary as (

    select
        m.current_tier_name,
        count(distinct m.customer_id) as member_count,
        avg(co.total_spend) as avg_lifetime_spend,
        avg(co.order_count) as avg_order_count,
        avg(co.avg_order_value) as avg_order_value,
        sum(co.total_spend) as total_tier_revenue
    from members as m
    left join customer_orders as co on m.customer_id = co.customer_id
    group by 1

),

final as (

    select
        current_tier_name,
        member_count,
        avg_lifetime_spend,
        avg_order_count,
        avg_order_value,
        total_tier_revenue,
        avg_lifetime_spend - lag(avg_lifetime_spend) over (order by avg_lifetime_spend)
            as incremental_value_vs_lower_tier,
        cast(total_tier_revenue as {{ dbt.type_float() }})
            / nullif(sum(total_tier_revenue) over (), 0) * 100 as revenue_share_pct
    from tier_summary

)

select * from final
