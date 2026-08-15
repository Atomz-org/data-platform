with

gift_cards as (

    select * from {{ ref('dim_gift_cards') }}

),

liability_summary as (

    select
        gift_card_status,
        is_expired,
        is_fully_redeemed,
        count(gift_card_id) as card_count,
        sum(initial_balance) as total_initial_balance,
        sum(total_redeemed) as total_redeemed,
        sum(latest_balance) as total_outstanding_balance,
        avg(latest_balance) as avg_outstanding_balance,
        sum(
            case
                when not is_expired and not is_fully_redeemed
                then latest_balance
                else 0
            end
        ) as active_liability

    from gift_cards
    group by 1, 2, 3

),

totals as (

    select
        *,
        sum(active_liability) over () as total_active_liability,
        sum(total_outstanding_balance) over () as grand_total_outstanding

    from liability_summary

)

select * from totals
