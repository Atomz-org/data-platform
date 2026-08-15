with

loyalty_members as (

    select * from {{ ref('dim_loyalty_members') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

-- Tag orders as loyalty or non-loyalty
order_loyalty_flag as (

    select
        orders.order_id,
        orders.customer_id,
        orders.order_total,
        orders.ordered_at,
        {{ dbt.date_trunc('month', 'orders.ordered_at') }} as order_month,
        case
            when loyalty_members.loyalty_member_id is not null
                and loyalty_members.is_active_member
            then true
            else false
        end as is_loyalty_customer

    from orders

    left join loyalty_members
        on orders.customer_id = loyalty_members.customer_id

),

-- Monthly revenue by loyalty status
monthly_revenue as (

    select
        order_month,
        is_loyalty_customer,
        sum(order_total) as total_revenue,
        count(distinct order_id) as total_orders,
        count(distinct customer_id) as unique_customers,
        avg(order_total) as avg_order_value

    from order_loyalty_flag
    group by 1, 2

),

-- Monthly totals for share calculation
monthly_totals as (

    select
        order_month,
        sum(total_revenue) as month_total_revenue,
        sum(total_orders) as month_total_orders

    from monthly_revenue
    group by 1

),

-- Final with share metrics
final as (

    select
        monthly_revenue.order_month,
        monthly_revenue.is_loyalty_customer,
        monthly_revenue.total_revenue,
        monthly_revenue.total_orders,
        monthly_revenue.unique_customers,
        monthly_revenue.avg_order_value,
        monthly_totals.month_total_revenue,
        monthly_totals.month_total_orders,
        -- Revenue share
        case
            when monthly_totals.month_total_revenue > 0
            then monthly_revenue.total_revenue / monthly_totals.month_total_revenue
            else 0
        end as revenue_share,
        -- Order share
        case
            when monthly_totals.month_total_orders > 0
            then monthly_revenue.total_orders * 1.0 / monthly_totals.month_total_orders
            else 0
        end as order_share,
        -- Revenue per customer
        case
            when monthly_revenue.unique_customers > 0
            then monthly_revenue.total_revenue / monthly_revenue.unique_customers
            else null
        end as revenue_per_customer

    from monthly_revenue

    inner join monthly_totals
        on monthly_revenue.order_month = monthly_totals.order_month

)

select * from final
order by order_month, is_loyalty_customer
