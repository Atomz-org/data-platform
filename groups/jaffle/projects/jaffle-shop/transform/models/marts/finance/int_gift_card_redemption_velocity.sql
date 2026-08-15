with

gift_card_payments as (

    select
        payment_transaction_id,
        gift_card_id,
        order_id,
        payment_amount,
        payment_status,
        processed_date

    from {{ ref('stg_payment_transactions') }}
    where gift_card_id is not null
      and payment_status = 'completed'

),

ordered_transactions as (

    select
        gift_card_id,
        processed_date,
        payment_amount,
        row_number() over (
            partition by gift_card_id
            order by processed_date
        ) as txn_sequence,
        lag(processed_date) over (
            partition by gift_card_id
            order by processed_date
        ) as prev_transaction_date,
        {{ sf_datediff('day', "(lag(processed_date) over ( partition by gift_card_id order by processed_date ))", "processed_date") }} as days_between_uses

    from gift_card_payments

),

velocity_per_card as (

    select
        gift_card_id,
        count(*) as total_transactions,
        sum(payment_amount) as total_redeemed,
        avg(payment_amount) as avg_transaction_amount,
        min(processed_date) as first_use_date,
        max(processed_date) as last_use_date,
        {{ sf_datediff('day', "(min(processed_date))", "(max(processed_date))") }} as active_span_days,
        round(avg(days_between_uses))::integer as avg_days_between_uses,
        min(days_between_uses)::integer as min_days_between_uses,
        max(days_between_uses)::integer as max_days_between_uses,
        case
            when {{ sf_datediff('day', "(min(processed_date))", "(max(processed_date))") }} > 0
                then count(*)::float / {{ sf_datediff('day', "(min(processed_date))", "(max(processed_date))") }}
            else null
        end as transactions_per_day

    from ordered_transactions
    group by 1

)

select * from velocity_per_card
