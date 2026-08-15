with

expenses as (

    select * from {{ ref('stg_expenses') }}

),

expense_categories as (

    select * from {{ ref('stg_expense_categories') }}

),

monthly_expenses as (

    select
        e.location_id,
        e.expense_category_id,
        ec.category_name,
        ec.is_operating_expense,
        ec.is_cost_of_goods_sold,
        {{ dbt.date_trunc('month', 'e.incurred_date') }} as expense_month,
        count(e.expense_id) as expense_count,
        sum(e.expense_amount) as total_expense_amount,
        avg(e.expense_amount) as avg_expense_amount,
        min(e.expense_amount) as min_expense_amount,
        max(e.expense_amount) as max_expense_amount

    from expenses as e
    left join expense_categories as ec
        on e.expense_category_id = ec.expense_category_id
    group by 1, 2, 3, 4, 5, 6

)

select * from monthly_expenses
