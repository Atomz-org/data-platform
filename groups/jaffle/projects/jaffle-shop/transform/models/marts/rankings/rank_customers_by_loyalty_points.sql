with

lm as (
    select * from {{ ref('dim_loyalty_members') }}
),

pb as (
    select * from {{ ref('int_loyalty_points_balance') }}
),

member_points as (
    select
        lm.customer_id,
        lm.loyalty_member_id,
        coalesce(pb.total_points_earned, 0) as points_balance,
        lm.current_tier_name
    from lm
    left join pb on lm.loyalty_member_id = pb.loyalty_member_id
),

ranked as (
    select
        customer_id,
        loyalty_member_id,
        points_balance,
        current_tier_name,
        rank() over (order by points_balance desc) as points_rank,
        ntile(10) over (order by points_balance desc) as points_decile
    from member_points
)

select * from ranked
