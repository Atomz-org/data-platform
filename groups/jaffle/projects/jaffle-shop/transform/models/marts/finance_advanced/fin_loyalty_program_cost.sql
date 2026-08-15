with

o as (
    select * from {{ ref('stg_orders') }}
),

lm as (
    select * from {{ ref('dim_loyalty_members') }}
),

points_issued as (

    select
        {{ dbt.date_trunc('month', 'transacted_at') }} as txn_month,
        sum(case when transaction_type = 'earn' then points else 0 end) as total_points_issued,
        sum(case when transaction_type = 'redeem' then points else 0 end) as total_points_redeemed
    from {{ ref('fct_loyalty_transactions') }}
    group by 1

),

loyalty_revenue as (

    select
        {{ dbt.date_trunc('month', 'o.ordered_at') }} as order_month,
        sum(o.order_total) as loyalty_member_revenue
    from o
    inner join lm
        on o.customer_id = lm.customer_id
    group by 1

),

current_liability as (

    select
        sum(current_points_balance) as total_outstanding_points
    from {{ ref('int_loyalty_points_balance') }}

),

final as (

    select
        pi.txn_month,
        pi.total_points_issued,
        pi.total_points_redeemed,
        -- Assume 1 point = $0.01 value
        pi.total_points_issued * 0.01 as points_issued_cost,
        pi.total_points_redeemed * 0.01 as points_redeemed_value,
        coalesce(lr.loyalty_member_revenue, 0) as loyalty_member_revenue,
        case
            when pi.total_points_issued * 0.01 > 0
            then coalesce(lr.loyalty_member_revenue, 0) / (pi.total_points_issued * 0.01)
            else null
        end as revenue_per_dollar_spent_on_loyalty,
        cl.total_outstanding_points,
        cl.total_outstanding_points * 0.01 as outstanding_liability
    from points_issued as pi
    left join loyalty_revenue as lr
        on pi.txn_month = lr.order_month
    cross join current_liability as cl

)

select * from final
