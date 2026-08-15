select sum(order_total) as total_revenue from {{ ref('stg_orders') }}
