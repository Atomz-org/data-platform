select avg(order_total) as avg_order_value from {{ ref('stg_orders') }}
