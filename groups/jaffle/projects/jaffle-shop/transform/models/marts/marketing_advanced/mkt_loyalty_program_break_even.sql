with

monthly_txns as (

    select
        {{ dbt.date_trunc('month', 'transacted_at') }} as txn_month,
        sum(case when transaction_type = 'earn' then points else 0 end) as points_earned,
        sum(case when transaction_type = 'redeem' then points else 0 end) as points_redeemed
    from {{ ref('fct_loyalty_transactions') }}
    group by 1

),

cumulative as (

    select
        txn_month,
        points_earned,
        points_redeemed,
        sum(points_earned) over (order by txn_month) as cumulative_earned,
        sum(points_redeemed) over (order by txn_month) as cumulative_redeemed,
        -- Breakage = earned - redeemed historically
        sum(points_earned) over (order by txn_month)
            - sum(points_redeemed) over (order by txn_month) as outstanding_points
    from monthly_txns

),

final as (

    select
        txn_month,
        points_earned,
        points_redeemed,
        cumulative_earned,
        cumulative_redeemed,
        outstanding_points,
        case
            when cumulative_earned > 0
            then cast(cumulative_redeemed as {{ dbt.type_float() }}) / cumulative_earned * 100
            else 0
        end as cumulative_redemption_rate_pct,
        -- Estimated breakage: if redemption rate stabilizes, unredeemed may never be used
        outstanding_points * 0.01 as estimated_breakage_value_dollars,
        points_earned * 0.01 as monthly_cost_dollars,
        points_redeemed * 0.01 as monthly_redemption_value_dollars
    from cumulative

)

select * from final
