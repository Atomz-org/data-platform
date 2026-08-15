with

gift_card_balances as (

    select * from {{ ref('int_gift_card_running_balance') }}

),

latest_balance as (

    select
        gift_card_id,
        card_number,
        customer_id,
        gift_card_status,
        initial_balance,
        issued_date,
        expires_date,
        running_balance_after as latest_balance,
        processed_date as last_redemption_date,
        row_number() over (
            partition by gift_card_id
            order by processed_date desc
        ) as rn

    from gift_card_balances

),

final as (

    select
        gift_card_id,
        card_number,
        customer_id,
        gift_card_status,
        initial_balance,
        latest_balance,
        initial_balance - latest_balance as total_redeemed,
        issued_date,
        expires_date,
        last_redemption_date,
        case
            when expires_date < current_date then true
            else false
        end as is_expired,
        case
            when latest_balance <= 0 then true
            else false
        end as is_fully_redeemed

    from latest_balance
    where rn = 1

)

select * from final
