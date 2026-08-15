with

loyalty_transactions as (

    select * from {{ ref('fct_loyalty_transactions') }}

),

-- Generate month boundaries from transaction data
months as (

    select distinct
        {{ dbt.date_trunc('month', 'transacted_at') }} as month_start

    from loyalty_transactions

),

-- Cumulative balance per member at end of each month
monthly_balance as (

    select
        m.month_start,
        lt.loyalty_member_id,
        lt.customer_id,
        sum(lt.points) as end_of_month_balance,
        sum(
            case when lt.transaction_type = 'earn' then lt.points else 0 end
        ) as points_earned_cumulative,
        sum(
            case when lt.transaction_type = 'redeem' then abs(lt.points) else 0 end
        ) as points_redeemed_cumulative,
        -- Activity within the month only
        sum(
            case
                when {{ dbt.date_trunc('month', 'lt.transacted_at') }} = m.month_start
                    and lt.transaction_type = 'earn'
                then lt.points
                else 0
            end
        ) as points_earned_in_month,
        sum(
            case
                when {{ dbt.date_trunc('month', 'lt.transacted_at') }} = m.month_start
                    and lt.transaction_type = 'redeem'
                then abs(lt.points)
                else 0
            end
        ) as points_redeemed_in_month,
        count(
            case
                when {{ dbt.date_trunc('month', 'lt.transacted_at') }} = m.month_start
                then lt.loyalty_transaction_id
            end
        ) as transactions_in_month

    from months as m

    inner join loyalty_transactions as lt
        on lt.transacted_at <= m.month_start + interval '1 month' - interval '1 day'

    group by 1, 2, 3

)

select * from monthly_balance
