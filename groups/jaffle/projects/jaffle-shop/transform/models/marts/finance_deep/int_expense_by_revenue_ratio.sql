with

expense_monthly as (

    select
        location_id,
        expense_month,
        category_name,
        total_expense_amount
    from {{ ref('int_expense_summary_monthly') }}

),

revenue as (

    select
        location_id,
        revenue_date,
        total_revenue
    from {{ ref('int_daily_revenue') }}

),

monthly_revenue as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'revenue_date') }} as revenue_month,
        sum(total_revenue) as monthly_revenue
    from revenue
    group by 1, 2

),

final as (

    select
        em.location_id,
        em.expense_month,
        em.category_name,
        em.total_expense_amount,
        coalesce(mr.monthly_revenue, 0) as monthly_revenue,
        case
            when coalesce(mr.monthly_revenue, 0) > 0
                then round(cast(em.total_expense_amount / mr.monthly_revenue * 100 as {{ dbt.type_float() }}), 2)
            else null
        end as expense_to_revenue_pct
    from expense_monthly as em
    left join monthly_revenue as mr
        on em.location_id = mr.location_id
        and em.expense_month = mr.revenue_month

)

select * from final
