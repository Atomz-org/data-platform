with

daily_spend as (

    select * from {{ ref('int_marketing_spend_daily') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

-- Aggregate daily spend to monthly
monthly_spend as (

    select
        {{ dbt.date_trunc('month', 'spend_date') }} as spend_month,
        sum(channel_spend) as total_monthly_spend,
        count(distinct spend_date) as active_spend_days,
        count(distinct spend_channel) as channels_used

    from daily_spend
    group by 1

),

-- Monthly revenue from orders
monthly_revenue as (

    select
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month,
        sum(order_total) as total_monthly_revenue,
        count(distinct order_id) as total_orders,
        count(distinct customer_id) as unique_customers

    from orders
    group by 1

),

-- Combine spend and revenue by month
final as (

    select
        coalesce(monthly_spend.spend_month, monthly_revenue.order_month) as month,
        coalesce(monthly_spend.total_monthly_spend, 0) as marketing_spend,
        coalesce(monthly_revenue.total_monthly_revenue, 0) as revenue,
        coalesce(monthly_revenue.total_orders, 0) as order_count,
        coalesce(monthly_revenue.unique_customers, 0) as unique_customers,
        monthly_spend.active_spend_days,
        monthly_spend.channels_used,
        -- Spend as percentage of revenue
        case
            when coalesce(monthly_revenue.total_monthly_revenue, 0) > 0
            then coalesce(monthly_spend.total_monthly_spend, 0) / monthly_revenue.total_monthly_revenue
            else null
        end as spend_to_revenue_ratio,
        -- Revenue per dollar spent
        case
            when coalesce(monthly_spend.total_monthly_spend, 0) > 0
            then monthly_revenue.total_monthly_revenue / monthly_spend.total_monthly_spend
            else null
        end as revenue_per_spend_dollar,
        -- Cost per order
        case
            when coalesce(monthly_revenue.total_orders, 0) > 0
            then coalesce(monthly_spend.total_monthly_spend, 0) / monthly_revenue.total_orders
            else null
        end as cost_per_order,
        -- Cost per customer
        case
            when coalesce(monthly_revenue.unique_customers, 0) > 0
            then coalesce(monthly_spend.total_monthly_spend, 0) / monthly_revenue.unique_customers
            else null
        end as cost_per_customer

    from monthly_spend

    full outer join monthly_revenue
        on monthly_spend.spend_month = monthly_revenue.order_month

)

select * from final
order by month
