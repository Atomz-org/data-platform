with

churn_scores as (

    select * from {{ ref('scr_customer_churn_propensity') }}

),

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

)

select
    cs.customer_id,
    c.customer_name,
    cs.churn_propensity_score,
    c.lifetime_spend,
    c.last_order_at,
    c.total_orders,
    'at_risk' as email_segment,
    current_timestamp as exported_at

from churn_scores cs
inner join customer_360 c on cs.customer_id = c.customer_id
where cs.churn_propensity_score > 70
