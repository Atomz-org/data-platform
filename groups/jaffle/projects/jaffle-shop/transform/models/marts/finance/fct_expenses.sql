with

expenses as (

    select * from {{ ref('stg_expenses') }}

),

expense_categories as (

    select * from {{ ref('stg_expense_categories') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

final as (

    select
        e.expense_id,
        e.location_id,
        l.location_name,
        e.expense_category_id,
        ec.category_name,
        ec.is_operating_expense,
        ec.is_cost_of_goods_sold,
        e.expense_description,
        e.vendor,
        e.expense_amount,
        e.incurred_date,
        {{ dbt.date_trunc('month', 'e.incurred_date') }} as expense_month

    from expenses as e
    left join expense_categories as ec
        on e.expense_category_id = ec.expense_category_id
    left join locations as l
        on e.location_id = l.location_id

)

select * from final
