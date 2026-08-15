with

loyalty_members as (

    select * from {{ ref('dim_loyalty_members') }}

),

churn_risk as (

    select * from {{ ref('int_loyalty_churn_risk') }}

),

loyalty_balance as (

    select * from {{ ref('int_loyalty_points_balance') }}

),

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

)

select
    lm.loyalty_member_id,
    lm.customer_id,
    c.customer_name,
    lm.current_tier_name,
    lm.enrolled_at,
    lm.membership_status,
    lb.current_points_balance,
    lb.total_points_earned,
    lb.total_points_redeemed,
    c.lifetime_spend,
    c.total_orders,
    coalesce(cr.days_since_last_transaction, 999) as loyalty_churn_risk,
    case
        when coalesce(cr.days_since_last_transaction, 999) > 70 then 'high_risk'
        when coalesce(cr.days_since_last_transaction, 999) > 40 then 'medium_risk'
        else 'low_risk'
    end as churn_risk_tier

from loyalty_members lm
left join customer_360 c on lm.customer_id = c.customer_id
left join churn_risk cr on lm.loyalty_member_id = cr.loyalty_member_id
left join loyalty_balance lb on lm.loyalty_member_id = lb.loyalty_member_id
