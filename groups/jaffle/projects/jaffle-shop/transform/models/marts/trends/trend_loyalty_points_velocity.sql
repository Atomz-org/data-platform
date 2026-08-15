with

daily_points as (
    select
        transacted_at,
        sum(case when transaction_type = 'earn' then points else 0 end) as points_earned,
        sum(case when transaction_type = 'redeem' then points else 0 end) as points_redeemed,
        count(distinct loyalty_member_id) as active_members
    from {{ ref('fct_loyalty_transactions') }}
    group by 1
),

trended as (
    select
        transacted_at,
        points_earned,
        points_redeemed,
        points_earned - points_redeemed as net_points,
        active_members,
        avg(points_earned) over (order by transacted_at rows between 6 preceding and current row) as earned_7d_ma,
        avg(points_redeemed) over (order by transacted_at rows between 6 preceding and current row) as redeemed_7d_ma,
        avg(points_earned - points_redeemed) over (order by transacted_at rows between 27 preceding and current row) as net_points_28d_ma,
        case
            when points_redeemed > points_earned * 1.5 then 'high_redemption'
            when points_earned > points_redeemed * 3 then 'high_earning'
            else 'balanced'
        end as points_flow_status
    from daily_points
)

select * from trended
