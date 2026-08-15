with

items as (
    select
        menu_item_id,
        menu_item_name as item_name,
        menu_item_price as current_price,
        category_name
    from {{ ref('dim_menu_items') }}
),

categories as (
    select
        category_name,
        avg(menu_item_price) as category_avg_price,
        min(menu_item_price) as category_min_price,
        max(menu_item_price) as category_max_price
    from {{ ref('dim_menu_items') }}
    group by 1
),

final as (
    select
        i.menu_item_id,
        i.item_name,
        i.current_price,
        i.category_name,
        c.category_avg_price,
        c.category_min_price,
        c.category_max_price,
        round(i.current_price - c.category_avg_price, 2) as price_vs_category_avg,
        case
            when i.current_price > c.category_avg_price * 1.2 then 'premium'
            when i.current_price < c.category_avg_price * 0.8 then 'value'
            else 'competitive'
        end as price_positioning
    from items as i
    inner join categories as c on i.category_name = c.category_name
)

select * from final
