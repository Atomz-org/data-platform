with 
c as (
    select * from {{ ref('stg_customers') }}
),

loyalty_data as (
    select
        loyalty_member_id,
        customer_id,
        current_tier_name as current_tier,
        enrolled_at,
        {{ dbt.datediff("enrolled_at", "current_timestamp", "day") }} as membership_tenure_days
    from {{ ref('dim_loyalty_members') }}
),

points as (
    select
        loyalty_member_id,
        current_points_balance as points_balance
    from {{ ref('int_loyalty_points_balance') }}
),

tier_progression as (
    select
        loyalty_member_id,
        customer_id,
        current_tier_name as previous_tier,
        earned_tier_name as new_tier,
        last_activity_at as transition_date,
        0 as months_in_previous_tier
    from {{ ref('int_loyalty_tier_progression') }}
),

latest_tier_change as (
    select
        customer_id,
        previous_tier,
        new_tier,
        transition_date,
        months_in_previous_tier,
        row_number() over (partition by customer_id order by transition_date desc) as rn
    from tier_progression
)

select
    c.customer_id,
    c.customer_name,
    ld.loyalty_member_id as member_id,
    ld.current_tier,
    ld.enrolled_at as loyalty_enrolled_at,
    ld.membership_tenure_days,
    coalesce(p.points_balance, 0) as loyalty_points_balance,
    ltc.previous_tier as last_tier_before_current,
    ltc.transition_date as last_tier_change_date,
    ltc.months_in_previous_tier,
    case
        when ld.loyalty_member_id is null then 'non_member'
        when ld.membership_tenure_days < 90 then 'new_member'
        when ld.membership_tenure_days < 365 then 'established_member'
        else 'veteran_member'
    end as loyalty_lifecycle_stage
from c
left join loyalty_data as ld
    on c.customer_id = ld.customer_id
left join points as p
    on ld.loyalty_member_id = p.loyalty_member_id
left join latest_tier_change as ltc
    on c.customer_id = ltc.customer_id
    and ltc.rn = 1
