with

daily_revenue as (

    select
        revenue_date,
        sum(total_revenue) as daily_revenue

    from {{ ref('int_daily_revenue') }}
    group by revenue_date

),

daily_expenses as (

    select
        {{ dbt.date_trunc('day', 'incurred_date') }} as expense_date,
        sum(expense_amount) as daily_expenses

    from {{ ref('fct_expenses') }}
    group by 1

),

comparison as (

    select
        coalesce(r.revenue_date, e.expense_date) as check_date,
        coalesce(r.daily_revenue, 0) as daily_revenue,
        coalesce(e.daily_expenses, 0) as daily_expenses,
        case
            when coalesce(r.daily_revenue, 0) > 0
            then coalesce(e.daily_expenses, 0) * 1.0 / r.daily_revenue
            else null
        end as expense_to_revenue_ratio

    from daily_revenue as r

    full outer join daily_expenses as e
        on r.revenue_date = e.expense_date

),

anomalies as (

    select
        *,
        case
            when daily_revenue = 0 and daily_expenses > 0 then 'expenses_without_revenue'
            when expense_to_revenue_ratio >= 2.0 then 'expenses_exceed_2x_revenue'
            else 'normal'
        end as anomaly_type

    from comparison

    where (daily_revenue = 0 and daily_expenses > 0)
       or expense_to_revenue_ratio >= 2.0

)

select * from anomalies
