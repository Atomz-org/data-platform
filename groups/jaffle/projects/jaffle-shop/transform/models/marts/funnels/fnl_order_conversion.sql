with

orders as (

    select * from {{ ref('stg_orders') }}

),

-- Use order status as proxy for funnel stages
-- Assume statuses represent progression: placed → completed → returned
order_funnel as (

    select
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month,
        count(distinct order_id) as total_orders_placed,
        count(distinct case
            when order_total_cents > 0 then order_id
        end) as orders_with_revenue,
        count(distinct case
            when subtotal_cents > 0 and tax_paid_cents >= 0 then order_id
        end) as orders_fulfilled,
        count(distinct customer_id) as unique_customers
    from orders
    group by 1

),

with_conversion_rates as (

    select
        order_month,
        total_orders_placed,
        orders_with_revenue,
        orders_fulfilled,
        unique_customers,
        case
            when total_orders_placed > 0
            then round(orders_with_revenue * 100.0 / total_orders_placed, 2)
            else 0
        end as revenue_capture_rate_pct,
        case
            when orders_with_revenue > 0
            then round(orders_fulfilled * 100.0 / orders_with_revenue, 2)
            else 0
        end as fulfillment_rate_pct,
        case
            when unique_customers > 0
            then round(total_orders_placed * 1.0 / unique_customers, 2)
            else 0
        end as orders_per_customer
    from order_funnel

)

select * from with_conversion_rates
