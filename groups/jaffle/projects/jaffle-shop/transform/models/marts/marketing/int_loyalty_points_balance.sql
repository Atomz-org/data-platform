with

loyalty_transactions as (

    select * from {{ ref('stg_loyalty_transactions') }}

),

-- Calculate running points balance per member
running_balance as (

    select
        loyalty_member_id,
        loyalty_transaction_id,
        transaction_type,
        points,
        transacted_at,
        sum(points) over (
            partition by loyalty_member_id
            order by transacted_at, loyalty_transaction_id
            rows unbounded preceding
        ) as running_points_balance

    from loyalty_transactions

),

-- Get latest balance and lifetime stats per member
member_balance_summary as (

    select
        loyalty_member_id,
        sum(case when transaction_type = 'earn' then points else 0 end) as total_points_earned,
        sum(case when transaction_type = 'redeem' then abs(points) else 0 end) as total_points_redeemed,
        sum(case when transaction_type = 'expire' then abs(points) else 0 end) as total_points_expired,
        sum(case when transaction_type = 'bonus' then points else 0 end) as total_bonus_points,
        sum(points) as current_points_balance,
        count(loyalty_transaction_id) as total_transactions,
        min(transacted_at) as first_transaction_date,
        max(transacted_at) as last_transaction_date

    from loyalty_transactions
    group by 1

)

select * from member_balance_summary
