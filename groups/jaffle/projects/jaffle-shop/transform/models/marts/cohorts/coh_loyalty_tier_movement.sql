with

tier_progression as (

    select * from {{ ref('int_loyalty_tier_progression') }}

),

-- Create monthly snapshots of tier status by using last_activity_at as proxy
member_monthly as (

    select
        loyalty_member_id,
        customer_id,
        current_tier_name,
        earned_tier_name,
        enrolled_at,
        last_activity_at,
        {{ dbt.date_trunc('month', 'last_activity_at') }} as activity_month
    from tier_progression
    where last_activity_at is not null

),

-- Lookup: for each earned_tier_name, find a representative current_tier_name
-- (used to determine if a member's current tier is below the earned tier)
earned_tier_lookup as (

    select
        earned_tier_name,
        min(current_tier_name) as reference_tier_name
    from tier_progression
    where earned_tier_name is not null
    group by 1

),

tier_transitions as (

    select
        mm.loyalty_member_id,
        mm.customer_id,
        mm.current_tier_name,
        mm.earned_tier_name,
        mm.activity_month,
        case
            when mm.current_tier_name = mm.earned_tier_name then 'maintained'
            when mm.earned_tier_name is null then 'unknown'
            when mm.current_tier_name != mm.earned_tier_name
                and mm.current_tier_name < coalesce(etl.reference_tier_name, '')
            then 'upgrade_pending'
            else 'maintained'
        end as tier_movement_type
    from member_monthly as mm
    left join earned_tier_lookup as etl
        on mm.earned_tier_name = etl.earned_tier_name

),

monthly_summary as (

    select
        activity_month,
        current_tier_name as tier_name,
        count(distinct loyalty_member_id) as member_count,
        count(distinct case when tier_movement_type = 'maintained' then loyalty_member_id end) as maintained_count,
        count(distinct case when tier_movement_type = 'upgrade_pending' then loyalty_member_id end) as upgrade_pending_count
    from tier_transitions
    group by 1, 2

)

select * from monthly_summary
