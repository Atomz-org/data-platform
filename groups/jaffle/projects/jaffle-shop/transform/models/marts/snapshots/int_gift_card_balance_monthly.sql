with

gift_card_running as (

    select * from {{ ref('int_gift_card_running_balance') }}

),

-- Generate month boundaries from gift card activity
months as (

    select distinct
        {{ dbt.date_trunc('month', 'processed_date') }} as month_start

    from gift_card_running

),

-- Latest balance per gift card per month
latest_balance_per_month as (

    select
        m.month_start,
        gc.gift_card_id,
        gc.card_number,
        gc.customer_id,
        gc.gift_card_status,
        gc.initial_balance,
        gc.running_balance_after,
        gc.daily_redemption_amount,
        gc.processed_date,
        row_number() over (
            partition by m.month_start, gc.gift_card_id
            order by gc.processed_date desc
        ) as recency_rank

    from months as m

    inner join gift_card_running as gc
        on gc.processed_date <= m.month_start + interval '1 month' - interval '1 day'

),

monthly_snapshot as (

    select
        month_start,
        gift_card_id,
        card_number,
        customer_id,
        gift_card_status,
        initial_balance,
        running_balance_after as end_of_month_balance,
        initial_balance - running_balance_after as total_redeemed_to_date

    from latest_balance_per_month
    where recency_rank = 1

)

select * from monthly_snapshot
