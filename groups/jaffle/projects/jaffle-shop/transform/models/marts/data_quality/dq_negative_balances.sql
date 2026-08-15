with

gift_cards as (
    select
        gift_card_id,
        card_number,
        customer_id,
        gift_card_status,
        initial_balance,
        latest_balance,
        'gift_card' as balance_type
    from {{ ref('dim_gift_cards') }}
    where latest_balance < 0
),

loyalty_points as (
    select * from {{ ref('int_loyalty_points_balance') }}
),

loyalty_members as (
    select * from {{ ref('dim_loyalty_members') }}
),

loyalty_balance as (
    select
        lb.loyalty_member_id,
        lm.customer_id,
        null as account_status,
        0 as initial_balance,
        lb.current_points_balance,
        'loyalty_points' as balance_type
    from loyalty_points as lb
    left join loyalty_members as lm
        on lb.loyalty_member_id = lm.loyalty_member_id
    where lb.current_points_balance < 0
),

combined as (
    select
        gift_card_id::text as account_id,
        card_number,
        customer_id,
        gift_card_status as account_status,
        initial_balance,
        latest_balance as current_balance,
        balance_type
    from gift_cards

    union all

    select
        loyalty_member_id::text as account_id,
        null as card_number,
        customer_id,
        account_status,
        initial_balance::numeric,
        current_points_balance::numeric as current_balance,
        balance_type
    from loyalty_balance
)

select * from combined
