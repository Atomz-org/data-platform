with monthly as (
    select
        {{ sf_date_trunc('month', "transacted_at") }} as txn_month,
        count(distinct loyalty_member_id) as active_members,
        sum(case when transaction_type = 'earn' then points else 0 end) as points_earned,
        sum(case when transaction_type = 'redeem' then points else 0 end) as points_redeemed
    from {{ ref('fct_loyalty_transactions') }}
    group by 1
),
final as (
    select
        {{ sf_date_trunc('quarter', "txn_month") }} as txn_quarter,
        round(avg(active_members), 0) as avg_monthly_members,
        sum(points_earned) as quarterly_points_earned,
        sum(points_redeemed) as quarterly_points_redeemed
    from monthly
    group by 1
)
select * from final
