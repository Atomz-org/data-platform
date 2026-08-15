with

lifecycle as (

    select
        customer_id,
        lifecycle_stage,
        total_orders,
        days_since_last_order,
        lifetime_spend
    from {{ ref('mkt_customer_lifecycle_stage') }}

),

comm_pref as (

    select
        customer_id,
        preferred_channel
    from {{ ref('mkt_customer_communication_preference') }}

),

final as (

    select
        l.customer_id,
        l.lifecycle_stage,
        l.total_orders,
        l.days_since_last_order,
        l.lifetime_spend,
        coalesce(cp.preferred_channel, 'email_preferred') as preferred_channel,
        case
            when lifecycle_stage = 'prospect' then 'send_welcome_offer'
            when lifecycle_stage = 'new_customer' then 'send_second_purchase_incentive'
            when lifecycle_stage = 'active' and total_orders > 5 then 'loyalty_upgrade_offer'
            when lifecycle_stage = 'active' then 'cross_sell_recommendation'
            when lifecycle_stage = 'at_risk' then 'send_retention_offer'
            when lifecycle_stage = 'churned' then 'send_win_back_campaign'
            when lifecycle_stage = 'win_back' then 'send_exclusive_return_offer'
            else 'general_engagement'
        end as next_best_action,
        case
            when lifecycle_stage in ('at_risk', 'churned') then 'high'
            when lifecycle_stage in ('new_customer', 'win_back') then 'medium'
            else 'low'
        end as action_urgency
    from lifecycle as l
    left join comm_pref as cp on l.customer_id = cp.customer_id

)

select * from final
