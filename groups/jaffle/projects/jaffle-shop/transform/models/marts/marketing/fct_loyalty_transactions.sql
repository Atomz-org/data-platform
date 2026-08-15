with

loyalty_transactions as (

    select * from {{ ref('stg_loyalty_transactions') }}

),

loyalty_members as (

    select * from {{ ref('stg_loyalty_members') }}

),

final as (

    select
        loyalty_transactions.loyalty_transaction_id,
        loyalty_transactions.loyalty_member_id,
        loyalty_transactions.order_id,
        loyalty_transactions.transaction_type,
        loyalty_transactions.transaction_description,
        loyalty_transactions.points,
        loyalty_transactions.transacted_at,

        -- Member context
        loyalty_members.customer_id,
        loyalty_members.membership_status,
        loyalty_members.current_tier_id,
        loyalty_members.enrolled_at,

        -- Running balance at time of transaction
        sum(loyalty_transactions.points) over (
            partition by loyalty_transactions.loyalty_member_id
            order by loyalty_transactions.transacted_at, loyalty_transactions.loyalty_transaction_id
            rows unbounded preceding
        ) as running_points_balance

    from loyalty_transactions

    left join loyalty_members
        on loyalty_transactions.loyalty_member_id = loyalty_members.loyalty_member_id

)

select * from final
