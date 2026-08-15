select max(ordered_at) as latest_order_date from {{ ref('stg_orders') }}
