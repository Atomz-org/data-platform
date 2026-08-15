with

balances as (

    select
        loyalty_member_id,
        current_points_balance as points_balance
    from {{ ref('int_loyalty_points_balance') }}

),

-- Assume 1 point = $0.01
final as (

    select
        count(*) as total_members_with_balance,
        sum(points_balance) as total_outstanding_points,
        sum(points_balance) * 0.01 as total_liability_dollars,
        avg(points_balance) as avg_points_per_member,
        avg(points_balance) * 0.01 as avg_liability_per_member,
        max(points_balance) as max_points_balance,
        max(points_balance) * 0.01 as max_liability_single_member,
        sum(case when points_balance > 1000 then 1 else 0 end) as high_balance_members,
        sum(case when points_balance > 1000 then points_balance else 0 end) * 0.01
            as high_balance_liability
    from balances
    where points_balance > 0

)

select * from final
