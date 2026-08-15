with

orders as (

    select * from {{ ref('orders') }}

),

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

)

select
    o.order_id,
    o.ordered_at,
    o.order_total,
    o.tax_paid,
    o.location_id,
    o.customer_id,
    c.customer_name,
    c.ltv_tier as customer_segment,
    c.lifetime_spend as lifetime_value,
    c.total_orders as customer_total_orders,
    c.rfm_segment_code as rfm_segment,
    c.loyalty_tier,
    c.rfm_total_score as churn_risk_score,
    c.first_order_at as first_order_date,
    c.days_since_last_order

from orders o
left join customer_360 c on o.customer_id = c.customer_id
