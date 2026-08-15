with monthly_active as (
    select
        {{ sf_date_trunc('month', "transacted_at") }} as txn_month,
        count(distinct loyalty_member_id) as active_members
    from {{ ref('fct_loyalty_transactions') }}
    group by 1
),
total_members as (
    select count(distinct loyalty_member_id) as total_enrolled from {{ ref('dim_loyalty_members') }}
),
final as (
    select
        a.txn_month,
        a.active_members,
        t.total_enrolled,
        round(a.active_members * 100.0 / nullif(t.total_enrolled, 0), 2) as active_rate_pct
    from monthly_active as a
    cross join total_members as t
)
select * from final
