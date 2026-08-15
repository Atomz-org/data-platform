with

product_sales as (

    select
        product_id,
        product_name,
        product_type,
        sum(units_sold) as total_units_sold,
        sum(daily_revenue) as total_revenue,
        sum(order_count) as total_orders
    from {{ ref('fct_product_sales') }}
    group by 1, 2, 3

),

margin as (

    select
        menu_item_id,
        menu_item_name,
        category_name,
        gross_margin_pct
    from {{ ref('int_menu_item_margin') }}

),

categories as (

    select
        menu_category_id,
        category_name
    from {{ ref('dim_menu_categories') }}

),

-- Category averages
category_avg as (

    select
        m.category_name,
        avg(ps.total_units_sold) as cat_avg_units,
        avg(ps.total_revenue) as cat_avg_revenue,
        avg(m.gross_margin_pct) as cat_avg_margin_pct,
        count(distinct ps.product_id) as products_in_category
    from product_sales as ps
    inner join margin as m
        on ps.product_name = m.menu_item_name
    group by 1

),

comparison as (

    select
        ps.product_id,
        ps.product_name,
        m.category_name,
        ps.total_units_sold,
        ps.total_revenue,
        m.gross_margin_pct as product_margin_pct,

        ca.cat_avg_units,
        ca.cat_avg_revenue,
        ca.cat_avg_margin_pct,
        ca.products_in_category,

        -- Vs category
        ps.total_units_sold - ca.cat_avg_units as units_vs_category,
        ps.total_revenue - ca.cat_avg_revenue as revenue_vs_category,
        m.gross_margin_pct - ca.cat_avg_margin_pct as margin_vs_category_pp,

        -- Index (100 = category average)
        case
            when ca.cat_avg_revenue > 0
            then round(ps.total_revenue / ca.cat_avg_revenue * 100, 1)
            else null
        end as revenue_index,
        case
            when ca.cat_avg_units > 0
            then round(ps.total_units_sold * 1.0 / ca.cat_avg_units * 100, 1)
            else null
        end as units_index

    from product_sales as ps
    inner join margin as m
        on ps.product_name = m.menu_item_name
    inner join category_avg as ca
        on m.category_name = ca.category_name

)

select * from comparison
