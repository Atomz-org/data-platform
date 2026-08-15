with

source as (

    select * from {{ source('finance', 'raw_expense_categories') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as expense_category_id,

        ---------- text
        name as category_name,
        description as category_description,

        ---------- booleans
        coalesce(is_operating, false) as is_operating_expense,
        coalesce(is_cogs, false) as is_cost_of_goods_sold

    from source

)

select * from renamed
