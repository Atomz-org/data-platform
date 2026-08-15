with

gift_cards as (

    select
        gift_card_id,
        customer_id,
        gift_card_status,
        initial_balance,
        latest_balance,
        total_redeemed,
        issued_date,
        expires_date,
        last_redemption_date,
        is_expired,
        is_fully_redeemed,
        {{ dbt.datediff('issued_date', 'current_date', 'day') }} as days_since_issued,
        {{ dbt.datediff('last_redemption_date', 'current_date', 'day') }} as days_since_last_use
    from {{ ref('dim_gift_cards') }}

),

breakage_estimate as (

    select
        gift_card_id,
        customer_id,
        initial_balance,
        latest_balance,
        total_redeemed,
        issued_date,
        expires_date,
        last_redemption_date,
        days_since_issued,
        days_since_last_use,
        is_expired,
        is_fully_redeemed,
        case
            when is_fully_redeemed then 0
            when is_expired then latest_balance
            when days_since_last_use > 365 then latest_balance * 0.95
            when days_since_last_use > 180 then latest_balance * 0.75
            when days_since_last_use > 90 then latest_balance * 0.50
            when days_since_issued > 365 then latest_balance * 0.40
            else latest_balance * 0.10
        end as estimated_breakage_amount,
        case
            when is_fully_redeemed then 'fully_redeemed'
            when is_expired then 'expired'
            when days_since_last_use > 365 then 'likely_abandoned'
            when days_since_last_use > 180 then 'high_risk'
            when days_since_last_use > 90 then 'moderate_risk'
            else 'low_risk'
        end as breakage_risk_category
    from gift_cards

)

select
    gift_card_id,
    customer_id,
    initial_balance,
    latest_balance,
    total_redeemed,
    issued_date,
    expires_date,
    last_redemption_date,
    days_since_issued,
    days_since_last_use,
    breakage_risk_category,
    estimated_breakage_amount,
    initial_balance - total_redeemed - estimated_breakage_amount as expected_future_redemption
from breakage_estimate
