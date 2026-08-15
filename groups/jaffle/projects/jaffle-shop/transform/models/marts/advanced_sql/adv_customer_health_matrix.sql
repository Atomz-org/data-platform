-- adv_customer_health_matrix.sql
-- Technique: Complex nested CASE expressions for multi-dimensional classification
-- Creates a 27-segment customer health matrix by crossing three dimensions:
--   Frequency (high/medium/low) x Recency (active/cooling/dormant) x Monetary (high/medium/low)
-- Each dimension is derived from RFM quintile scores (1-5), then combined into
-- a single composite segment label. This pattern is common in CRM systems where
-- business rules map numeric scores to actionable categories.

with rfm as (

    select * from {{ ref('int_customer_rfm_scores') }}

),

-- Step 1: Map each RFM quintile (1-5) to a business-friendly tier
classified as (

    select
        customer_id,
        days_since_last_order,
        order_count,
        total_spend,
        recency_score,
        frequency_score,
        monetary_score,
        rfm_total_score,

        -- Frequency dimension: how often do they buy?
        case
            when frequency_score >= 4 then 'high'
            when frequency_score >= 2 then 'medium'
            else 'low'
        end as frequency_tier,

        -- Recency dimension: how recently did they buy?
        case
            when recency_score >= 4 then 'active'
            when recency_score >= 2 then 'cooling'
            else 'dormant'
        end as recency_tier,

        -- Monetary dimension: how much do they spend?
        case
            when monetary_score >= 4 then 'high'
            when monetary_score >= 2 then 'medium'
            else 'low'
        end as monetary_tier

    from rfm

),

-- Step 2: Combine the three dimensions into a composite health segment
-- with a nested CASE that produces actionable business recommendations
health_matrix as (

    select
        *,

        -- Composite segment label
        recency_tier || '_' || frequency_tier || '_' || monetary_tier as health_segment,

        -- Nested CASE: map the 27 combinations to strategic actions
        case
            -- Champions: active + high frequency + high monetary
            when recency_tier = 'active' and frequency_tier = 'high' and monetary_tier = 'high'
                then 'champion'
            when recency_tier = 'active' and frequency_tier = 'high' and monetary_tier = 'medium'
                then 'loyal_customer'
            when recency_tier = 'active' and frequency_tier = 'high' and monetary_tier = 'low'
                then 'frequent_buyer'

            -- Active medium frequency
            when recency_tier = 'active' and frequency_tier = 'medium' and monetary_tier = 'high'
                then 'big_spender'
            when recency_tier = 'active' and frequency_tier = 'medium' and monetary_tier = 'medium'
                then 'promising'
            when recency_tier = 'active' and frequency_tier = 'medium' and monetary_tier = 'low'
                then 'new_customer'

            -- Active low frequency
            when recency_tier = 'active' and frequency_tier = 'low' and monetary_tier = 'high'
                then 'high_potential'
            when recency_tier = 'active' and frequency_tier = 'low' and monetary_tier = 'medium'
                then 'recent_visitor'
            when recency_tier = 'active' and frequency_tier = 'low' and monetary_tier = 'low'
                then 'newcomer'

            -- Cooling high frequency — at risk of churning
            when recency_tier = 'cooling' and frequency_tier = 'high' and monetary_tier = 'high'
                then 'at_risk_champion'
            when recency_tier = 'cooling' and frequency_tier = 'high' and monetary_tier = 'medium'
                then 'at_risk_loyal'
            when recency_tier = 'cooling' and frequency_tier = 'high' and monetary_tier = 'low'
                then 'at_risk_frequent'

            -- Cooling medium frequency
            when recency_tier = 'cooling' and frequency_tier = 'medium' and monetary_tier = 'high'
                then 'needs_attention_high'
            when recency_tier = 'cooling' and frequency_tier = 'medium' and monetary_tier = 'medium'
                then 'needs_attention'
            when recency_tier = 'cooling' and frequency_tier = 'medium' and monetary_tier = 'low'
                then 'about_to_sleep'

            -- Cooling low frequency
            when recency_tier = 'cooling' and frequency_tier = 'low' and monetary_tier = 'high'
                then 'cooling_high_value'
            when recency_tier = 'cooling' and frequency_tier = 'low' and monetary_tier = 'medium'
                then 'cooling_medium'
            when recency_tier = 'cooling' and frequency_tier = 'low' and monetary_tier = 'low'
                then 'drifting_away'

            -- Dormant high frequency — lost valuable customers
            when recency_tier = 'dormant' and frequency_tier = 'high' and monetary_tier = 'high'
                then 'lost_champion'
            when recency_tier = 'dormant' and frequency_tier = 'high' and monetary_tier = 'medium'
                then 'lost_loyal'
            when recency_tier = 'dormant' and frequency_tier = 'high' and monetary_tier = 'low'
                then 'lost_frequent'

            -- Dormant medium frequency
            when recency_tier = 'dormant' and frequency_tier = 'medium' and monetary_tier = 'high'
                then 'hibernating_high_value'
            when recency_tier = 'dormant' and frequency_tier = 'medium' and monetary_tier = 'medium'
                then 'hibernating'
            when recency_tier = 'dormant' and frequency_tier = 'medium' and monetary_tier = 'low'
                then 'hibernating_low'

            -- Dormant low frequency — lowest priority
            when recency_tier = 'dormant' and frequency_tier = 'low' and monetary_tier = 'high'
                then 'lost_high_spender'
            when recency_tier = 'dormant' and frequency_tier = 'low' and monetary_tier = 'medium'
                then 'lost'
            when recency_tier = 'dormant' and frequency_tier = 'low' and monetary_tier = 'low'
                then 'lost_cheap'

            else 'unclassified'
        end as health_label,

        -- Recommended action based on the composite segment
        case
            when recency_tier = 'active' and frequency_tier = 'high'
                then 'reward_and_retain'
            when recency_tier = 'active' and frequency_tier in ('medium', 'low') and monetary_tier = 'high'
                then 'upsell_frequency'
            when recency_tier = 'active'
                then 'nurture_and_grow'
            when recency_tier = 'cooling' and (frequency_tier = 'high' or monetary_tier = 'high')
                then 'win_back_urgently'
            when recency_tier = 'cooling'
                then 'reactivation_campaign'
            when recency_tier = 'dormant' and (frequency_tier = 'high' or monetary_tier = 'high')
                then 'aggressive_win_back'
            when recency_tier = 'dormant'
                then 'low_priority_reactivation'
            else 'review_manually'
        end as recommended_action

    from classified

)

select
    customer_id,
    days_since_last_order,
    order_count,
    total_spend,
    recency_score,
    frequency_score,
    monetary_score,
    rfm_total_score,
    recency_tier,
    frequency_tier,
    monetary_tier,
    health_segment,
    health_label,
    recommended_action
from health_matrix
order by rfm_total_score desc, total_spend desc
