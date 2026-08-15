with

menu_items as (

    select * from {{ ref('stg_menu_items') }}

),

menu_categories as (

    select * from {{ ref('stg_menu_categories') }}

),

nutritional_info as (

    select * from {{ ref('stg_nutritional_info') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

enriched as (

    select
        mi.menu_item_id,
        mi.product_id,
        mi.menu_category_id,
        mi.menu_item_name,
        mi.menu_item_description,
        mi.menu_item_size,
        mi.menu_item_price,
        mi.display_order,
        mi.is_available,
        mi.is_combo,
        mi.is_seasonal,
        mc.category_name,
        mc.parent_category_id,
        mc.category_depth,
        p.product_name,
        p.product_type,
        p.is_food_item,
        p.is_drink_item,
        ni.calories,
        ni.total_fat_g,
        ni.sodium_mg,
        ni.total_sugars_g,
        ni.protein_g,
        ni.caffeine_mg,
        ni.serving_size_description

    from menu_items as mi
    left join menu_categories as mc
        on mi.menu_category_id = mc.menu_category_id
    left join nutritional_info as ni
        on mi.menu_item_id = ni.menu_item_id
    left join products as p
        on mi.product_id = p.product_id

)

select * from enriched
