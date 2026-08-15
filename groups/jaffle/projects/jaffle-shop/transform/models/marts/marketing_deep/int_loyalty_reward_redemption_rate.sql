with

loyalty_txns as (

    select * from {{ ref('stg_loyalty_transactions') }}

),

member_summary as (

    select
        loyalty_member_id,
        sum(case when transaction_type = 'earn' then points else 0 end) as total_points_earned,
        sum(case when transaction_type = 'redeem' then abs(points) else 0 end) as total_points_redeemed,
        count(case when transaction_type = 'earn' then 1 end) as earn_transactions,
        count(case when transaction_type = 'redeem' then 1 end) as redeem_transactions
    from loyalty_txns
    group by 1

),

final as (

    select
        loyalty_member_id,
        total_points_earned,
        total_points_redeemed,
        total_points_earned - total_points_redeemed as points_outstanding,
        earn_transactions,
        redeem_transactions,
        case
            when total_points_earned > 0
                then round(cast(total_points_redeemed * 100.0 / total_points_earned as {{ dbt.type_float() }}), 2)
            else 0
        end as redemption_rate_pct,
        case
            when total_points_earned > 0 and total_points_redeemed * 100.0 / total_points_earned > 75
                then 'high_redeemer'
            when total_points_earned > 0 and total_points_redeemed * 100.0 / total_points_earned > 25
                then 'moderate_redeemer'
            when total_points_redeemed > 0
                then 'low_redeemer'
            else 'non_redeemer'
        end as redemption_behavior
    from member_summary

)

select * from final
