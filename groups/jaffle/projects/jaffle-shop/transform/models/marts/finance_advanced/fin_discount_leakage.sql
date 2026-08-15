with

coupon_costs as (

    select
        {{ dbt.date_trunc('month', 'redeemed_at') }} as redemption_month,
        sum(discount_applied) as total_discount_given
    from {{ ref('fct_coupon_redemptions') }}
    group by 1

),

budget_discount as (

    select
        {{ dbt.date_trunc('month', 'budget_month') }} as budget_month,
        sum(case when budget_type = 'marketing' then budgeted_amount else 0 end) as budgeted_marketing_spend
    from {{ ref('stg_budgets') }}
    group by 1

),

final as (

    select
        cc.redemption_month,
        cc.total_discount_given,
        coalesce(bd.budgeted_marketing_spend, 0) as budgeted_marketing_spend,
        cc.total_discount_given - coalesce(bd.budgeted_marketing_spend, 0) as discount_variance,
        case
            when coalesce(bd.budgeted_marketing_spend, 0) > 0
            then (cc.total_discount_given / bd.budgeted_marketing_spend) * 100
            else null
        end as discount_utilization_pct,
        case
            when cc.total_discount_given > coalesce(bd.budgeted_marketing_spend, 0)
            then 'over_budget'
            else 'within_budget'
        end as leakage_flag
    from coupon_costs as cc
    left join budget_discount as bd
        on cc.redemption_month = bd.budget_month

)

select * from final
