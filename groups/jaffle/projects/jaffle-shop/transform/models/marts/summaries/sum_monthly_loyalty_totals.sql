with final as (
    select
        {{ sf_date_trunc('month', "transacted_at") }} as txn_month,
        count(distinct loyalty_member_id) as active_members,
        sum(case when transaction_type = 'earn' then points else 0 end) as points_earned,
        sum(case when transaction_type = 'redeem' then points else 0 end) as points_redeemed,
        sum(case when transaction_type = 'earn' then points else 0 end) - sum(case when transaction_type = 'redeem' then points else 0 end) as net_points,
        count(*) as total_transactions
    from {{ ref('fct_loyalty_transactions') }}
    group by 1
)
select * from final
