with

source as (

    select * from {{ source('product', 'raw_menu_items') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as menu_item_id,
        cast(product_id as varchar) as product_id,
        cast(category_id as varchar) as menu_category_id,

        ---------- text
        name as menu_item_name,
        description as menu_item_description,
        size as menu_item_size,

        ---------- numerics
        {{ cents_to_dollars('price') }} as menu_item_price,
        display_order,

        ---------- booleans
        coalesce(is_available, false) as is_available,
        coalesce(is_combo, false) as is_combo,
        coalesce(is_seasonal, false) as is_seasonal

    from source

)

select * from renamed
