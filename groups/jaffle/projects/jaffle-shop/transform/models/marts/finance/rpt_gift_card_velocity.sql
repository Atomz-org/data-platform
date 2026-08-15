with

gift_cards as (

    select * from {{ ref('dim_gift_cards') }}

),

velocity as (

    select * from {{ ref('int_gift_card_redemption_velocity') }}

),

issuance_trend as (

    select
        {{ dbt.date_trunc('month', 'issued_date') }} as report_month,
        count(gift_card_id) as cards_issued,
        sum(initial_balance) as total_issued_value,
        avg(initial_balance) as avg_issued_value

    from gift_cards
    group by 1

),

redemption_trend as (

    select
        {{ dbt.date_trunc('month', 'first_use_date') }} as first_use_month,
        count(gift_card_id) as cards_first_used,
        sum(total_redeemed) as total_redeemed_amount,
        avg(avg_transaction_amount) as avg_txn_amount,
        avg(avg_days_between_uses) as avg_days_between_uses,
        avg(total_transactions) as avg_transactions_per_card,
        avg(active_span_days) as avg_active_span_days

    from velocity
    group by 1

),

combined as (

    select
        coalesce(it.report_month, rt.first_use_month) as report_month,
        coalesce(it.cards_issued, 0) as cards_issued,
        coalesce(it.total_issued_value, 0) as total_issued_value,
        it.avg_issued_value,
        coalesce(rt.cards_first_used, 0) as cards_first_used,
        coalesce(rt.total_redeemed_amount, 0) as total_redeemed_amount,
        rt.avg_txn_amount,
        rt.avg_days_between_uses,
        rt.avg_transactions_per_card,
        rt.avg_active_span_days,
        coalesce(it.total_issued_value, 0)
            - coalesce(rt.total_redeemed_amount, 0) as net_liability_change,
        case
            when coalesce(it.cards_issued, 0) > 0
                then coalesce(rt.cards_first_used, 0)::float / it.cards_issued
            else null
        end as activation_rate

    from issuance_trend as it
    full outer join redemption_trend as rt
        on it.report_month = rt.first_use_month

)

select * from combined
