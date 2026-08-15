with

product_sales as (

    select * from {{ ref('fct_product_sales') }}

),

menu_items as (

    select * from {{ ref('stg_menu_items') }}

),

menu_categories as (

    select * from {{ ref('dim_menu_categories') }}

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

with_category as (

    select
        pt.product_id,
        pt.product_name,
        pt.product_type,
        mc.menu_category_id,
        mc.category_name,
        pt.total_units_sold,
        pt.total_revenue,
        rank() over (
            partition by mc.menu_category_id
            order by pt.total_units_sold desc
        ) as volume_rank_in_category,
        rank() over (
            partition by mc.menu_category_id
            order by pt.total_revenue desc
        ) as revenue_rank_in_category,
        rank() over (
            order by pt.total_units_sold desc
        ) as overall_volume_rank,
        rank() over (
            order by pt.total_revenue desc
        ) as overall_revenue_rank

    from product_totals as pt
    inner join menu_items as mi
        on pt.product_id = mi.product_id
    inner join menu_categories as mc
        on mi.menu_category_id = mc.menu_category_id

)

select * from with_category
