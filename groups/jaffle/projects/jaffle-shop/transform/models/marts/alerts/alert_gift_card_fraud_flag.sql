with

gc as (
    select * from {{ ref('dim_gift_cards') }}
),

gc_activity as (
    select
        gc.gift_card_id,
        gc.initial_balance,
        gc.latest_balance,
        gc.issued_date,
        gc.initial_balance - gc.latest_balance as total_spent,
        case
            when gc.initial_balance - gc.latest_balance > gc.initial_balance * 0.9
                and {{ sf_datediff('day', "gc.issued_date", "current_date") }} < 2
            then true
            else false
        end as rapid_drain_flag,
        case
            when gc.initial_balance > 500 then true
            else false
        end as high_value_flag
    from gc
),

alerts as (
    select
        gift_card_id,
        initial_balance,
        latest_balance,
        total_spent,
        issued_date,
        'gift_card_fraud_flag' as alert_type,
        case when rapid_drain_flag and high_value_flag then 'critical' else 'warning' end as severity
    from gc_activity
    where rapid_drain_flag or high_value_flag
)

select * from alerts
