with

popularity as (

    select * from {{ ref('int_menu_item_popularity_rank') }}

),

menu_item_margin as (

    select * from {{ ref('int_menu_item_margin') }}

),

menu_items as (

    select * from {{ ref('stg_menu_items') }}

),

final as (

    select
        p.product_id,
        p.product_name,
        p.product_type,
        p.menu_category_id,
        p.category_name,
        p.total_units_sold,
        p.total_revenue,
        p.volume_rank_in_category,
        p.revenue_rank_in_category,
        p.overall_volume_rank,
        p.overall_revenue_rank,
        mim.menu_item_price,
        mim.total_ingredient_cost,
        mim.gross_margin,
        mim.gross_margin_pct,
        p.total_units_sold * mim.gross_margin as total_gross_profit,
        rank() over (
            partition by p.menu_category_id
            order by p.total_units_sold * mim.gross_margin desc
        ) as profit_rank_in_category

    from popularity as p
    inner join menu_items as mi
        on p.product_id = mi.product_id
    inner join menu_item_margin as mim
        on mi.menu_item_id = mim.menu_item_id

)

select * from final
