with

menu_items as (

    select * from {{ ref('dim_menu_items') }}

)

select
    menu_item_id,
    menu_item_name,
    menu_category_id,
    menu_item_price as price,
    is_available as is_active,
    menu_item_description as description,
    current_timestamp as synced_at,
    'recce_dw' as source_system

from menu_items
where is_available = true
