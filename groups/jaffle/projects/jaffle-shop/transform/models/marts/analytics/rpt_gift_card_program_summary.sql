with

gift_cards as (

    select * from {{ ref('stg_gift_cards') }}

),

monthly_issuance as (

    select
        {{ dbt.date_trunc('month', 'issued_date') }} as issue_month,
        count(gift_card_id) as cards_issued,
        sum(initial_balance) as total_issued_value,
        avg(initial_balance) as avg_initial_balance
    from gift_cards
    group by 1

),

program_totals as (

    select
        count(gift_card_id) as total_cards,
        count(case when gift_card_status = 'active' then 1 end) as active_cards,
        count(case when gift_card_status = 'redeemed' then 1 end) as fully_redeemed_cards,
        count(case when gift_card_status = 'expired' then 1 end) as expired_cards,
        sum(initial_balance) as total_issued_value,
        sum(current_balance) as total_outstanding_balance,
        sum(initial_balance) - sum(current_balance) as total_redeemed_value,
        case
            when sum(initial_balance) > 0
                then round(cast(
                    (sum(initial_balance) - sum(current_balance)) * 100.0 / sum(initial_balance)
                as {{ dbt.type_float() }}), 2)
            else 0
        end as overall_redemption_rate_pct,
        -- Breakage: expired cards with remaining balance
        sum(case when gift_card_status = 'expired' then current_balance else 0 end) as breakage_value
    from gift_cards

)

select * from program_totals
