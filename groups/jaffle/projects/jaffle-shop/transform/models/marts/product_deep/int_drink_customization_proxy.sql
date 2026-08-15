with

products as (

    select * from {{ ref('stg_products') }}

),

menu_categories as (

    select
        menu_category_id,
        category_name,
        parent_category_id
    from {{ ref('stg_menu_categories') }}

),

menu_items as (

    select
        menu_item_id,
        product_id,
        menu_category_id,
        menu_item_name,
        menu_item_size,
        is_available
    from {{ ref('stg_menu_items') }}

),

category_product_count as (

    select
        mc.menu_category_id,
        mc.category_name,
        p.product_type,
        count(distinct mi.product_id) as product_count,
        count(distinct mi.menu_item_id) as menu_item_count,
        count(distinct mi.menu_item_size) as size_variants
    from menu_items as mi
    inner join products as p
        on mi.product_id = p.product_id
    inner join menu_categories as mc
        on mi.menu_category_id = mc.menu_category_id
    where mi.is_available
    group by 1, 2, 3

),

final as (

    select
        menu_category_id,
        category_name,
        product_type,
        product_count,
        menu_item_count,
        size_variants,
        case
            when menu_item_count > product_count * 2 then 'high_variety'
            when menu_item_count > product_count then 'moderate_variety'
            else 'standard'
        end as variety_level
    from category_product_count

)

select * from final
