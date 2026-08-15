with

budgets as (
    select * from {{ ref('stg_budgets') }}
),

locations as (
    select location_id, location_name from {{ ref('stg_locations') }}
),

final as (
    select
        b.budget_id,
        b.location_id,
        l.location_name,
        b.expense_category_id,
        b.budget_month,
        b.budgeted_amount
    from budgets as b
    left join locations as l on b.location_id = l.location_id
)

select * from final
