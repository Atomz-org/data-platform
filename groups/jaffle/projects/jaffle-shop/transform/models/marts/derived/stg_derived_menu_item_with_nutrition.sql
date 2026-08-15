with

items as (
    select menu_item_id, product_id, menu_item_name, menu_item_price from {{ ref('stg_menu_items') }}
),

nutrition as (
    select * from {{ ref('stg_nutritional_info') }}
),

final as (
    select
        mi.menu_item_id,
        mi.product_id,
        mi.menu_item_name,
        mi.menu_item_price,
        n.calories,
        n.protein_g,
        n.total_fat_g,
        n.total_carbs_g,
        n.dietary_fiber_g,
        n.sodium_mg
    from items as mi
    left join nutrition as n on mi.menu_item_id = n.menu_item_id
)

select * from final
