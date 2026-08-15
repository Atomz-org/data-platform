with monthly_revenue as (
    select
        cast(location_id as {{ dbt.type_string() }}) as location_id,
        {{ dbt.date_trunc("month", "revenue_date") }} as month_start,
        sum(total_revenue) as monthly_revenue
    from {{ ref('int_revenue_by_store_daily') }}
    group by 1, {{ dbt.date_trunc("month", "revenue_date") }}
),

monthly_expenses as (
    select
        cast(location_id as {{ dbt.type_string() }}) as location_id,
        expense_month,
        sum(total_expense_amount) as total_monthly_expenses,
        count(distinct expense_category_id) as expense_category_count
    from {{ ref('int_expense_summary_monthly') }}
    group by 1, expense_month
),

monthly_labor as (
    select
        cast(location_id as {{ dbt.type_string() }}) as location_id,
        {{ dbt.date_trunc("month", "work_date") }} as labor_month,
        sum(total_labor_cost) as monthly_labor_cost,
        sum(total_hours) as monthly_hours_worked,
        sum(employee_count) as unique_employees
    from {{ ref('int_labor_cost_daily') }}
    group by 1, {{ dbt.date_trunc("month", "work_date") }}
)

select
    coalesce(cast(r.location_id as {{ dbt.type_string() }}), cast(e.location_id as {{ dbt.type_string() }}), cast(l.location_id as {{ dbt.type_string() }})) as location_id,
    coalesce(r.month_start, e.expense_month, l.labor_month) as month_start,
    coalesce(r.monthly_revenue, 0) as monthly_revenue,
    coalesce(e.total_monthly_expenses, 0) as monthly_expenses,
    coalesce(l.monthly_labor_cost, 0) as monthly_labor_cost,
    coalesce(l.monthly_hours_worked, 0) as monthly_hours_worked,
    coalesce(l.unique_employees, 0) as unique_employees,
    coalesce(r.monthly_revenue, 0)
        - coalesce(e.total_monthly_expenses, 0)
        - coalesce(l.monthly_labor_cost, 0) as net_operating_income,
    case
        when coalesce(r.monthly_revenue, 0) > 0
            then round(
                (coalesce(r.monthly_revenue, 0)
                    - coalesce(e.total_monthly_expenses, 0)
                    - coalesce(l.monthly_labor_cost, 0))
                / r.monthly_revenue * 100, 2
            )
        else 0
    end as operating_margin_pct
from monthly_revenue as r
full outer join monthly_expenses as e
    on r.location_id = e.location_id
    and r.month_start = e.expense_month
full outer join monthly_labor as l
    on coalesce(r.location_id, e.location_id) = l.location_id
    and coalesce(r.month_start, e.expense_month) = l.labor_month
