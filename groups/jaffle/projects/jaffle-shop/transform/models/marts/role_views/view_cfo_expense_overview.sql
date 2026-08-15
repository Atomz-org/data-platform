with

expenses as (

    select * from {{ ref('fct_expenses') }}

),

categories as (

    select * from {{ ref('dim_expense_categories') }}

),

monthly_expenses as (

    select
        {{ dbt.date_trunc('month', 'e.incurred_date') }} as expense_month,
        e.expense_category_id,
        c.category_name,
        e.location_id,
        sum(e.expense_amount) as total_amount,
        count(*) as transaction_count

    from expenses e
    left join categories c on e.expense_category_id = c.expense_category_id
    group by {{ dbt.date_trunc('month', 'e.incurred_date') }}, e.expense_category_id, c.category_name, e.location_id

)

select
    expense_month,
    expense_category_id,
    category_name,
    location_id,
    total_amount,
    transaction_count,
    round(
        (total_amount * 100.0
        / nullif(sum(total_amount) over (partition by expense_month), 0)), 2
    ) as pct_of_monthly_total

from monthly_expenses
