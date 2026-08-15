with

product_sales_daily as (

    select * from {{ ref('int_product_sales_daily') }}

),

menu_items as (

    select * from {{ ref('stg_menu_items') }}

),

menu_categories as (

    select * from {{ ref('stg_menu_categories') }}

),

sales_with_category as (

    select
        mc.menu_category_id,
        mc.category_name,
        mc.parent_category_id,
        mc.category_depth,
        psd.sale_date,
        psd.product_id,
        psd.product_name,
        psd.units_sold,
        psd.daily_revenue

    from product_sales_daily as psd
    inner join menu_items as mi
        on psd.product_id = mi.product_id
    inner join menu_categories as mc
        on mi.menu_category_id = mc.menu_category_id

),

category_summary as (

    select
        menu_category_id,
        category_name,
        parent_category_id,
        category_depth,
        -- NOTE: product count for category breadth metric
        count(product_id) as product_count,
        sum(units_sold) as total_units_sold,
        sum(daily_revenue) as total_revenue,
        avg(daily_revenue) as avg_daily_revenue,
        min(sale_date) as first_sale_date,
        max(sale_date) as last_sale_date,
        sum(daily_revenue) * 1.0
            / nullif(sum(sum(daily_revenue)) over (), 0)
            as revenue_share_pct

    from sales_with_category
    group by
        menu_category_id,
        category_name,
        parent_category_id,
        category_depth

)

select * from category_summary
