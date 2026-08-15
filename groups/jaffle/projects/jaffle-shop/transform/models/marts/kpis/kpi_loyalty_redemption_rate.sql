with monthly as (
    select
        {{ sf_date_trunc('month', "transacted_at") }} as txn_month,
        sum(case when transaction_type = 'redeem' then points else 0 end) as points_redeemed,
        sum(case when transaction_type = 'earn' then points else 0 end) as points_earned
    from {{ ref('fct_loyalty_transactions') }}
    group by 1
),
final as (
    select
        txn_month,
        points_earned,
        points_redeemed,
        round(points_redeemed * 100.0 / nullif(points_earned, 0), 2) as redemption_rate_pct
    from monthly
)
select * from final
