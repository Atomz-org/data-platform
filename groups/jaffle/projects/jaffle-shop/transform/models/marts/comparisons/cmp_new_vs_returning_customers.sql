with

orders as (

    select * from {{ ref('orders') }}

),

customers as (

    select * from {{ ref('customers') }}

),

order_enriched as (

    select
        o.order_id,
        o.customer_id,
        o.ordered_at,
        o.order_total,
        o.subtotal,
        o.count_order_items,
        o.customer_order_number,
        c.customer_type,
        {{ dbt.date_trunc('month', 'o.ordered_at') }} as order_month
    from orders as o
    inner join customers as c
        on o.customer_id = c.customer_id

),

segment_metrics as (

    select
        order_month,
        customer_type,
        count(distinct order_id) as total_orders,
        count(distinct customer_id) as unique_customers,
        sum(order_total) as total_revenue,
        avg(order_total) as avg_order_value,
        avg(count_order_items) as avg_items_per_order,
        sum(order_total) / nullif(count(distinct customer_id), 0) as revenue_per_customer
    from order_enriched
    group by 1, 2

),

pivoted as (

    select
        n.order_month,
        n.unique_customers as new_customers,
        n.total_orders as new_orders,
        n.total_revenue as new_revenue,
        n.avg_order_value as new_avg_order_value,
        n.avg_items_per_order as new_avg_items,
        r.unique_customers as returning_customers,
        r.total_orders as returning_orders,
        r.total_revenue as returning_revenue,
        r.avg_order_value as returning_avg_order_value,
        r.avg_items_per_order as returning_avg_items,
        round(
            (r.total_revenue * 100.0
            / nullif(n.total_revenue + r.total_revenue, 0)), 2
        ) as returning_revenue_share_pct,
        round(
            (r.unique_customers * 100.0
            / nullif(n.unique_customers + r.unique_customers, 0)), 2
        ) as returning_customer_share_pct
    from segment_metrics as n
    left join segment_metrics as r
        on n.order_month = r.order_month
        and r.customer_type = 'returning'
    where n.customer_type = 'new'

)

select * from pivoted
