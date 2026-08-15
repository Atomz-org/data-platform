with

gift_cards as (

    select * from {{ ref('stg_gift_cards') }}

),

gift_card_payments as (

    select
        gift_card_id,
        processed_date,
        payment_amount,
        payment_status

    from {{ ref('stg_payment_transactions') }}
    where gift_card_id is not null

),

redemptions as (

    select
        gift_card_id,
        processed_date,
        sum(
            case when payment_status = 'completed' then payment_amount else 0 end
        ) as daily_redemption_amount,
        count(*) as daily_transaction_count

    from gift_card_payments
    group by 1, 2

),

running_balance as (

    select
        gc.gift_card_id,
        gc.card_number,
        gc.customer_id,
        gc.gift_card_status,
        gc.initial_balance,
        gc.issued_date,
        gc.expires_date,
        r.processed_date,
        r.daily_redemption_amount,
        r.daily_transaction_count,
        gc.initial_balance - sum(r.daily_redemption_amount)
            over (
                partition by gc.gift_card_id
                order by r.processed_date
                rows between unbounded preceding and current row
            ) as running_balance_after

    from gift_cards as gc
    inner join redemptions as r
        on gc.gift_card_id = r.gift_card_id

)

select * from running_balance
