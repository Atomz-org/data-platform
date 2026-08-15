with

members as (

    select * from {{ ref('stg_loyalty_members') }}

),

loyalty_txns as (

    select * from {{ ref('stg_loyalty_transactions') }}

),

enrollment_summary as (

    select
        {{ dbt.date_trunc('month', 'enrolled_at') }} as enrollment_month,
        count(loyalty_member_id) as new_enrollments,
        count(case when membership_status = 'active' then 1 end) as active_members
    from members
    group by 1

),

activity_summary as (

    select
        {{ dbt.date_trunc('month', 'transacted_at') }} as activity_month,
        count(distinct loyalty_member_id) as active_members_transacting,
        sum(case when transaction_type = 'earn' then points else 0 end) as total_points_earned,
        sum(case when transaction_type = 'redeem' then abs(points) else 0 end) as total_points_redeemed,
        count(loyalty_transaction_id) as total_transactions
    from loyalty_txns
    group by 1

),

points_liability as (

    select
        sum(case when transaction_type = 'earn' then points else 0 end)
        - sum(case when transaction_type = 'redeem' then abs(points) else 0 end) as outstanding_points_liability
    from loyalty_txns

),

final as (

    select
        coalesce(es.enrollment_month, acts.activity_month) as report_month,
        coalesce(es.new_enrollments, 0) as new_enrollments,
        coalesce(es.active_members, 0) as active_members_enrolled,
        coalesce(acts.active_members_transacting, 0) as active_members_transacting,
        coalesce(acts.total_points_earned, 0) as total_points_earned,
        coalesce(acts.total_points_redeemed, 0) as total_points_redeemed,
        coalesce(acts.total_transactions, 0) as total_transactions,
        case
            when coalesce(acts.total_points_earned, 0) > 0
                then round(cast(
                    coalesce(acts.total_points_redeemed, 0) * 100.0
                    / acts.total_points_earned
                as {{ dbt.type_float() }}), 2)
            else 0
        end as monthly_redemption_rate
    from enrollment_summary as es
    full outer join activity_summary as acts
        on es.enrollment_month = acts.activity_month

)

select * from final
