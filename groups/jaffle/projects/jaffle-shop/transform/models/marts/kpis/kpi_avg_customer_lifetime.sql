with final as (
    select
        count(distinct customer_id) as total_customers,
        round(avg(customer_tenure_days), 0) as avg_tenure_days,
        round(avg(case when total_orders > 1 then customer_tenure_days end), 0) as avg_repeat_tenure_days,
        round(avg(lifetime_spend), 2) as avg_ltv,
        round(avg(total_orders), 1) as avg_order_count,
        round(avg(avg_order_value), 2) as avg_aov
    from {{ ref('dim_customer_360') }}
    where customer_tenure_days > 0
)
select * from final
