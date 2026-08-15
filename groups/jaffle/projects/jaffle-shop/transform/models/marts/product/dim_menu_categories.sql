with

menu_categories as (

    select * from {{ ref('stg_menu_categories') }}

),

parent_categories as (

    select
        menu_category_id,
        category_name as parent_category_name

    from menu_categories

),

final as (

    select
        mc.menu_category_id,
        mc.parent_category_id,
        mc.category_name,
        mc.category_description,
        mc.category_display_order,
        mc.category_depth,
        mc.is_active_category,
        pc.parent_category_name

    from menu_categories as mc
    left join parent_categories as pc
        on mc.parent_category_id = pc.menu_category_id

)

select * from final
