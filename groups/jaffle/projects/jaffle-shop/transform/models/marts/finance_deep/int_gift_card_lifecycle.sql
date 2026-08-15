with

gift_cards as (

    select * from {{ ref('stg_gift_cards') }}

),

usage_stats as (

    select
        gift_card_id,
        count(payment_transaction_id) as usage_count,
        sum(payment_amount) as total_spent
    from {{ ref('stg_payment_transactions') }}
    where gift_card_id is not null
    group by 1

),

final as (

    select
        gc.gift_card_id,
        gc.customer_id,
        gc.gift_card_status,
        gc.initial_balance,
        gc.current_balance,
        gc.issued_date,
        gc.expires_date,
        {{ dbt.datediff('gc.issued_date', dbt.current_timestamp(), 'day') }} as card_age_days,
        coalesce(us.usage_count, 0) as usage_count,
        coalesce(us.total_spent, 0) as total_spent,
        gc.initial_balance - gc.current_balance as amount_used,
        case
            when gc.initial_balance > 0
                then round(cast((gc.initial_balance - gc.current_balance) / gc.initial_balance * 100 as {{ dbt.type_float() }}), 2)
            else 0
        end as utilization_pct,
        case
            when gc.current_balance >= 50 then 'high_balance'
            when gc.current_balance >= 20 then 'medium_balance'
            when gc.current_balance > 0 then 'low_balance'
            else 'depleted'
        end as balance_tier
    from gift_cards as gc
    left join usage_stats as us
        on gc.gift_card_id = us.gift_card_id

)

select * from final
