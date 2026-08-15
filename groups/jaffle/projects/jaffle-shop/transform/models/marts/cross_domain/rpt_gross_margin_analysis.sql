with

menu_items_raw as (
    select * from {{ ref('dim_menu_items') }}
),

menu_categories_raw as (
    select * from {{ ref('dim_menu_categories') }}
),

product_sales_by_loc as (
    select * from {{ ref('int_product_sales_by_location') }}
),

product_margin as (
    select
        product_id,
        units_sold,
        daily_revenue,
        cogs_per_unit,
        total_cogs,
        gross_margin,
        gross_margin_per_unit,
        gross_margin_pct
    from {{ ref('int_gross_margin_by_product') }}
),

menu_info as (
    select
        mi.menu_item_id,
        mi.product_id,
        mi.menu_item_name,
        mc.menu_category_id,
        mc.category_name
    from menu_items_raw as mi
    inner join menu_categories_raw as mc
        on mi.menu_category_id = mc.menu_category_id
),

category_summary as (
    select
        mni.category_name,
        count(distinct pm.product_id) as products_in_category,
        sum(pm.daily_revenue) as category_revenue,
        sum(pm.total_cogs) as category_cogs,
        sum(pm.gross_margin) as category_gross_margin,
        avg(pm.gross_margin_pct) as avg_margin_pct,
        min(pm.gross_margin_pct) as min_margin_pct,
        max(pm.gross_margin_pct) as max_margin_pct
    from product_margin as pm
    inner join menu_info as mni on pm.product_id = mni.product_id
    group by mni.category_name
)

select * from category_summary
