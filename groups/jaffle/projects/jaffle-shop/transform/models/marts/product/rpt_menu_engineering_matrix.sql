with

product_sales as (

    select * from {{ ref('fct_product_sales') }}

),

menu_item_margin as (

    select * from {{ ref('int_menu_item_margin') }}

),

menu_items as (

    select * from {{ ref('stg_menu_items') }}

),

product_totals as (

    select
        product_id,
        product_name,
        product_type,
        sum(units_sold) as total_units_sold,
        sum(daily_revenue) as total_revenue

    from product_sales
    group by product_id, product_name, product_type

),

with_margin as (

    select
        pt.product_id,
        pt.product_name,
        pt.product_type,
        mim.menu_item_id,
        mim.menu_item_name,
        mim.category_name,
        mim.menu_item_price,
        mim.total_ingredient_cost,
        mim.gross_margin,
        mim.gross_margin_pct,
        pt.total_units_sold,
        pt.total_revenue,
        pt.total_units_sold * mim.gross_margin as total_gross_profit

    from product_totals as pt
    inner join menu_items as mi
        on pt.product_id = mi.product_id
    inner join menu_item_margin as mim
        on mi.menu_item_id = mim.menu_item_id

),

-- Calculate category medians for classification
category_medians as (

    select
        category_name,
        -- Use average as proxy for median
        avg(total_units_sold) as avg_category_volume,
        avg(gross_margin_pct) as avg_category_margin_pct

    from with_margin
    group by category_name

),

classified as (

    select
        wm.product_id,
        wm.product_name,
        wm.product_type,
        wm.menu_item_id,
        wm.menu_item_name,
        wm.category_name,
        wm.menu_item_price,
        wm.total_ingredient_cost,
        wm.gross_margin,
        wm.gross_margin_pct,
        wm.total_units_sold,
        wm.total_revenue,
        wm.total_gross_profit,
        cm.avg_category_volume,
        cm.avg_category_margin_pct,
        -- Menu engineering classification (BCG-style matrix)
        case
            when wm.total_units_sold >= cm.avg_category_volume
                and wm.gross_margin_pct >= cm.avg_category_margin_pct
            then 'star'           -- High popularity + High profitability
            when wm.total_units_sold < cm.avg_category_volume
                and wm.gross_margin_pct >= cm.avg_category_margin_pct
            then 'puzzle'         -- Low popularity + High profitability
            when wm.total_units_sold >= cm.avg_category_volume
                and wm.gross_margin_pct < cm.avg_category_margin_pct
            then 'plowhorse'      -- High popularity + Low profitability
            else 'dog'            -- Low popularity + Low profitability
        end as menu_engineering_class,
        -- Action recommendation
        case
            when wm.total_units_sold >= cm.avg_category_volume
                and wm.gross_margin_pct >= cm.avg_category_margin_pct
            then 'maintain_and_promote'
            when wm.total_units_sold < cm.avg_category_volume
                and wm.gross_margin_pct >= cm.avg_category_margin_pct
            then 'increase_visibility'
            when wm.total_units_sold >= cm.avg_category_volume
                and wm.gross_margin_pct < cm.avg_category_margin_pct
            then 'optimize_cost_or_raise_price'
            else 'consider_removal_or_revamp'
        end as recommended_action

    from with_margin as wm
    inner join category_medians as cm
        on wm.category_name = cm.category_name

)

select * from classified
