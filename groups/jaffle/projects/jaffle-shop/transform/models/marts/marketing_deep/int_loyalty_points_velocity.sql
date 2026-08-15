with

loyalty_txns as (

    select * from {{ ref('stg_loyalty_transactions') }}

),

monthly_points as (

    select
        loyalty_member_id,
        {{ dbt.date_trunc('month', 'transacted_at') }} as points_month,
        sum(case when transaction_type = 'earn' then points else 0 end) as points_earned,
        sum(case when transaction_type = 'redeem' then abs(points) else 0 end) as points_redeemed,
        sum(points) as net_points,
        count(loyalty_transaction_id) as transaction_count
    from loyalty_txns
    group by 1, 2

),

velocity as (

    select
        loyalty_member_id,
        points_month,
        points_earned,
        points_redeemed,
        net_points,
        transaction_count,
        avg(points_earned) over (
            partition by loyalty_member_id
            order by points_month
            rows between 2 preceding and current row
        ) as rolling_3m_avg_earned,
        case
            when points_earned > 0 then 'earning'
            when points_redeemed > 0 then 'redeeming'
            else 'inactive'
        end as monthly_activity_type
    from monthly_points

)

select * from velocity
