with 
c as (
    select * from {{ ref('stg_customers') }}
),

o as (
    select * from {{ ref('stg_orders') }}
),

oi as (
    select * from {{ ref('order_items') }}
),

customer_metrics as (
    select
        c.customer_id,
        {{ dbt.datediff("max(o.ordered_at)", "current_timestamp", "day") }} as days_since_last_order,
        count(distinct o.order_id) as order_count,
        coalesce(sum(oi.supply_cost), 0) as total_spend
    from c
    left join o
        on c.customer_id = o.customer_id
    left join oi
        on o.order_id = oi.order_id
    group by c.customer_id
),

percentiles as (
    select
        customer_id,
        days_since_last_order,
        order_count,
        total_spend,
        ntile(5) over (order by days_since_last_order desc) as recency_score,
        ntile(5) over (order by order_count asc) as frequency_score,
        ntile(5) over (order by total_spend asc) as monetary_score
    from customer_metrics
)

select
    customer_id,
    days_since_last_order,
    order_count,
    total_spend,
    recency_score,
    frequency_score,
    monetary_score,
    recency_score + frequency_score + monetary_score as rfm_total_score,
    cast(recency_score as {{ dbt.type_string() }})
        || cast(frequency_score as {{ dbt.type_string() }})
        || cast(monetary_score as {{ dbt.type_string() }}) as rfm_segment_code
from percentiles
