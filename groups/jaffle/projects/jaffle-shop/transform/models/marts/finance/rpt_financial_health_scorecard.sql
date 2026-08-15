with

daily_revenue as (

    select * from {{ ref('int_daily_revenue') }}

),

monthly_revenue as (

    select
        location_id,
        location_name,
        {{ dbt.date_trunc('month', 'revenue_date') }} as report_month,
        sum(total_revenue) as total_revenue

    from daily_revenue
    group by 1, 2, 3

),

revenue_growth as (

    select
        location_id,
        location_name,
        report_month,
        total_revenue,
        lag(total_revenue) over (
            partition by location_id
            order by report_month
        ) as prev_month_revenue,
        case
            when lag(total_revenue) over (
                partition by location_id
                order by report_month
            ) > 0
                then (total_revenue - lag(total_revenue) over (
                    partition by location_id
                    order by report_month
                )) / lag(total_revenue) over (
                    partition by location_id
                    order by report_month
                )
            else null
        end as revenue_growth_rate

    from monthly_revenue

),

expense_summary as (

    select
        location_id,
        expense_month as report_month,
        sum(total_expense_amount) as total_expenses

    from {{ ref('int_expense_summary_monthly') }}
    group by 1, 2

),

refund_rates as (

    select
        location_id,
        report_month,
        refund_rate,
        refund_amount_rate

    from {{ ref('int_refund_rate_by_store') }}

),

ar_aging as (

    select
        customer_id,
        sum(amount_outstanding) as total_outstanding,
        sum(case when aging_bucket_sort >= 4 then amount_outstanding else 0 end)
            as high_risk_outstanding

    from {{ ref('int_accounts_receivable_aging') }}
    group by 1

),

scorecard as (

    select
        rg.location_id,
        rg.location_name,
        rg.report_month,
        rg.total_revenue,
        rg.revenue_growth_rate,
        coalesce(es.total_expenses, 0) as total_expenses,
        case
            when rg.total_revenue > 0
                then coalesce(es.total_expenses, 0) / rg.total_revenue
            else null
        end as expense_ratio,
        coalesce(rr.refund_rate, 0) as refund_rate,
        coalesce(rr.refund_amount_rate, 0) as refund_amount_rate,

        -- Revenue growth score (0-25): >10% = 25, 5-10% = 20, 0-5% = 15, negative = 5
        case
            when rg.revenue_growth_rate > 0.10 then 25
            when rg.revenue_growth_rate > 0.05 then 20
            when rg.revenue_growth_rate > 0 then 15
            when rg.revenue_growth_rate is null then 10
            else 5
        end as revenue_growth_score,

        -- Expense ratio score (0-25): <40% = 25, 40-60% = 20, 60-80% = 15, >80% = 5
        case
            when rg.total_revenue > 0 and coalesce(es.total_expenses, 0) / rg.total_revenue < 0.40 then 25
            when rg.total_revenue > 0 and coalesce(es.total_expenses, 0) / rg.total_revenue < 0.60 then 20
            when rg.total_revenue > 0 and coalesce(es.total_expenses, 0) / rg.total_revenue < 0.80 then 15
            when rg.total_revenue > 0 then 5
            else 10
        end as expense_ratio_score,

        -- Refund rate score (0-25): <2% = 25, 2-5% = 20, 5-10% = 15, >10% = 5
        case
            when coalesce(rr.refund_rate, 0) < 0.02 then 25
            when coalesce(rr.refund_rate, 0) < 0.05 then 20
            when coalesce(rr.refund_rate, 0) < 0.10 then 15
            else 5
        end as refund_rate_score,

        -- Profitability score (0-25): net margin >20% = 25, 10-20% = 20, 0-10% = 15, negative = 5
        case
            when rg.total_revenue > 0
                and (rg.total_revenue - coalesce(es.total_expenses, 0)) / rg.total_revenue > 0.20
                then 25
            when rg.total_revenue > 0
                and (rg.total_revenue - coalesce(es.total_expenses, 0)) / rg.total_revenue > 0.10
                then 20
            when rg.total_revenue > 0
                and (rg.total_revenue - coalesce(es.total_expenses, 0)) / rg.total_revenue > 0
                then 15
            else 5
        end as profitability_score

    from revenue_growth as rg
    left join expense_summary as es
        on rg.location_id = es.location_id
        and rg.report_month = es.report_month
    left join refund_rates as rr
        on rg.location_id = rr.location_id
        and rg.report_month = rr.report_month

),

final as (

    select
        location_id,
        location_name,
        report_month,
        total_revenue,
        revenue_growth_rate,
        total_expenses,
        expense_ratio,
        refund_rate,
        refund_amount_rate,
        revenue_growth_score,
        expense_ratio_score,
        refund_rate_score,
        profitability_score,
        revenue_growth_score
            + expense_ratio_score
            + refund_rate_score
            + profitability_score as health_score,
        case
            when (revenue_growth_score + expense_ratio_score
                + refund_rate_score + profitability_score) >= 80 then 'excellent'
            when (revenue_growth_score + expense_ratio_score
                + refund_rate_score + profitability_score) >= 60 then 'good'
            when (revenue_growth_score + expense_ratio_score
                + refund_rate_score + profitability_score) >= 40 then 'fair'
            else 'poor'
        end as health_grade

    from scorecard

)

select * from final
