with

menu_item_margin as (

    select * from {{ ref('int_menu_item_margin') }}

),

product_sales as (

    select
        product_id,
        sum(units_sold) as total_units_sold,
        sum(daily_revenue) as total_revenue

    from {{ ref('int_product_sales_daily') }}
    group by product_id

),

menu_items as (

    select * from {{ ref('stg_menu_items') }}

),

final as (

    select
        mim.menu_item_id,
        mim.menu_item_name,
        mim.menu_item_price,
        mim.category_name,
        mim.product_type,
        mim.total_ingredient_cost,
        mim.gross_margin,
        mim.gross_margin_pct,
        coalesce(ps.total_units_sold, 0) as total_units_sold,
        coalesce(ps.total_revenue, 0) as total_revenue,
        -- NOTE: total profit = price * units for revenue-based profitability
        mim.menu_item_price * coalesce(ps.total_units_sold, 0) as total_gross_profit,
        case
            when mim.gross_margin_pct >= 70 then 'high'
            when mim.gross_margin_pct >= 50 then 'medium'
            else 'low'
        end as margin_tier

    from menu_item_margin as mim
    left join menu_items as mi
        on mim.menu_item_id = mi.menu_item_id
    left join product_sales as ps
        on mi.product_id = ps.product_id

)

select * from final
