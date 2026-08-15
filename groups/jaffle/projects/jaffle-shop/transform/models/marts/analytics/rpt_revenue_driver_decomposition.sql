with

orders as (

    select * from {{ ref('stg_orders') }}

),

monthly_metrics as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'ordered_at') }} as revenue_month,
        count(distinct customer_id) as unique_customers,
        count(order_id) as order_count,
        sum(order_total) as total_revenue,
        case
            when count(distinct customer_id) > 0
                then count(order_id) * 1.0 / count(distinct customer_id)
            else 0
        end as orders_per_customer,
        case
            when count(order_id) > 0
                then sum(order_total) * 1.0 / count(order_id)
            else 0
        end as avg_ticket_size
    from orders
    group by 1, 2

),

with_prior as (

    select
        *,
        lag(unique_customers) over (partition by location_id order by revenue_month) as prev_customers,
        lag(orders_per_customer) over (partition by location_id order by revenue_month) as prev_orders_per_customer,
        lag(avg_ticket_size) over (partition by location_id order by revenue_month) as prev_ticket_size,
        lag(total_revenue) over (partition by location_id order by revenue_month) as prev_revenue
    from monthly_metrics

),

final as (

    select
        location_id,
        revenue_month,
        total_revenue,
        prev_revenue,
        total_revenue - coalesce(prev_revenue, 0) as revenue_change,
        unique_customers,
        orders_per_customer,
        avg_ticket_size,
        unique_customers - coalesce(prev_customers, 0) as traffic_change,
        orders_per_customer - coalesce(prev_orders_per_customer, 0) as frequency_change,
        avg_ticket_size - coalesce(prev_ticket_size, 0) as ticket_change
    from with_prior

)

select * from final
