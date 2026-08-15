with

expense_categories as (

    select * from {{ ref('stg_expense_categories') }}

),

final as (

    select
        expense_category_id,
        category_name,
        category_description,
        is_operating_expense,
        is_cost_of_goods_sold,
        case
            when is_cost_of_goods_sold then 'COGS'
            when is_operating_expense then 'OpEx'
            else 'Other'
        end as expense_classification

    from expense_categories

)

select * from final
