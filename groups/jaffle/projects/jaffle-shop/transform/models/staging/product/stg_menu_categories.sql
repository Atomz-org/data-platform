with

source as (

    select * from {{ source('product', 'raw_menu_categories') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as menu_category_id,
        cast(parent_category_id as varchar) as parent_category_id,

        ---------- text
        name as category_name,
        description as category_description,

        ---------- numerics
        display_order as category_display_order,
        depth as category_depth,

        ---------- booleans
        coalesce(is_active, false) as is_active_category

    from source

)

select * from renamed
