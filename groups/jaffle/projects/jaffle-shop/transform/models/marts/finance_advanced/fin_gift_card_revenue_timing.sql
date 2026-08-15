with

gift_cards as (

    select
        gift_card_id,
        customer_id,
        initial_balance,
        latest_balance,
        total_redeemed,
        issued_date,
        last_redemption_date,
        case
            when last_redemption_date is not null
            then {{ dbt.datediff('issued_date', 'last_redemption_date', 'day') }}
            else null
        end as days_to_first_use
    from {{ ref('dim_gift_cards') }}

),

summary as (

    select
        {{ dbt.date_trunc('month', 'issued_date') }} as issue_month,
        count(*) as cards_issued,
        sum(initial_balance) as total_initial_value,
        sum(total_redeemed) as total_redeemed_value,
        sum(latest_balance) as total_remaining_balance,
        avg(days_to_first_use) as avg_days_to_use,
        sum(case when days_to_first_use <= 7 then 1 else 0 end) as used_within_7_days,
        sum(case when days_to_first_use <= 30 then 1 else 0 end) as used_within_30_days,
        sum(case when days_to_first_use <= 90 then 1 else 0 end) as used_within_90_days,
        sum(case when last_redemption_date is null then 1 else 0 end) as never_used
    from gift_cards
    group by 1

),

final as (

    select
        issue_month,
        cards_issued,
        total_initial_value,
        total_redeemed_value,
        total_remaining_balance,
        avg_days_to_use,
        used_within_7_days,
        used_within_30_days,
        used_within_90_days,
        never_used,
        case
            when cards_issued > 0
            then cast(never_used as {{ dbt.type_float() }}) / cards_issued * 100
            else 0
        end as never_used_pct,
        case
            when total_initial_value > 0
            then total_redeemed_value / total_initial_value * 100
            else 0
        end as redemption_rate_pct
    from summary

)

select * from final
