with

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

),

scored as (

    select
        customer_id,
        customer_name,

        -- Input signals
        days_since_last_order,
        total_orders,
        lifetime_spend,
        rfm_total_score,
        loyalty_tier,
        loyalty_lifecycle_stage,

        -- Recency component (0-30): higher days = higher churn risk
        {{ sf_least(["(round(coalesce(days_since_last_order, 365) * 30.0 / 365))", "30"]) }} as recency_score,

        -- Frequency trend component (0-25): fewer orders = higher risk
        case
            when coalesce(total_orders, 0) >= 20 then 0
            when coalesce(total_orders, 0) >= 10 then 5
            when coalesce(total_orders, 0) >= 5 then 10
            when coalesce(total_orders, 0) >= 2 then 18
            else 25
        end as frequency_score,

        -- Loyalty activity component (0-20): no loyalty = higher risk
        case
            when loyalty_lifecycle_stage = 'active' then 0
            when loyalty_lifecycle_stage = 'engaged' then 5
            when loyalty_lifecycle_stage = 'at_risk' then 12
            when loyalty_lifecycle_stage is null then 15
            else 20
        end as loyalty_score,

        -- Spend trend component (0-25): low avg order = higher risk
        case
            when coalesce(avg_order_value, 0) >= 50 then 0
            when coalesce(avg_order_value, 0) >= 30 then 5
            when coalesce(avg_order_value, 0) >= 15 then 12
            when coalesce(avg_order_value, 0) >= 5 then 18
            else 25
        end as spend_score

    from customer_360

),

final as (

    select
        customer_id,
        customer_name,
        days_since_last_order,
        total_orders,
        lifetime_spend,
        rfm_total_score,
        loyalty_tier,
        recency_score,
        frequency_score,
        loyalty_score,
        spend_score,
        {{ sf_least(["(recency_score + frequency_score + loyalty_score + spend_score)", "100"]) }} as churn_propensity_score,
        case
            when recency_score + frequency_score + loyalty_score + spend_score >= 70 then 'high'
            when recency_score + frequency_score + loyalty_score + spend_score >= 40 then 'medium'
            else 'low'
        end as churn_risk_tier

    from scored

)

select * from final
