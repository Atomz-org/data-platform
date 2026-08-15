with

expenses as (
    select * from {{ ref('stg_expenses') }}
),

categories as (
    select expense_category_id, category_name from {{ ref('stg_expense_categories') }}
),

final as (
    select
        ex.expense_id,
        ex.location_id,
        ex.expense_category_id,
        ec.category_name,
        ex.incurred_date,
        ex.expense_amount,
        ex.expense_description
    from expenses as ex
    left join categories as ec on ex.expense_category_id = ec.expense_category_id
)

select * from final
