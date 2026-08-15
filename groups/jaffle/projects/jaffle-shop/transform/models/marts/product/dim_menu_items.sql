with

menu_item_enriched as (

    select * from {{ ref('int_menu_item_enriched') }}

),

final as (

    select
        menu_item_id,
        product_id,
        menu_category_id,
        menu_item_name,
        menu_item_description,
        menu_item_size,
        menu_item_price,
        display_order,
        is_available,
        is_combo,
        is_seasonal,
        category_name,
        parent_category_id,
        category_depth,
        product_name,
        product_type,
        is_food_item,
        is_drink_item,
        calories,
        total_fat_g,
        sodium_mg,
        total_sugars_g,
        protein_g,
        caffeine_mg,
        serving_size_description

    from menu_item_enriched

)

select * from final
