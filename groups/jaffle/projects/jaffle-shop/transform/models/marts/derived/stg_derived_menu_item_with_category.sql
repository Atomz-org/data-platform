with

items as (
    select * from {{ ref('stg_menu_items') }}
),

categories as (
    select menu_category_id, category_name from {{ ref('stg_menu_categories') }}
),

final as (
    select
        mi.menu_item_id,
        mi.product_id,
        mi.menu_item_name,
        mi.menu_category_id,
        mc.category_name,
        mi.menu_item_price,
        mi.is_available
    from items as mi
    left join categories as mc on mi.menu_category_id = mc.menu_category_id
)

select * from final
