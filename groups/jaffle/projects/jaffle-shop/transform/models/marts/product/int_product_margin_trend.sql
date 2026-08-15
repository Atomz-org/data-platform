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

monthly_sales as (

    select
        {{ dbt.date_trunc('month', 'ps.sale_date') }} as sale_month,
        ps.product_id,
        ps.product_name,
        ps.product_type,
        sum(ps.units_sold) as monthly_units_sold,
        sum(ps.daily_revenue) as monthly_revenue,
        avg(ps.current_unit_price) as avg_selling_price

    from product_sales as ps
    group by
        {{ dbt.date_trunc('month', 'ps.sale_date') }},
        ps.product_id,
        ps.product_name,
        ps.product_type

),

with_margin as (

    select
        ms.sale_month,
        ms.product_id,
        ms.product_name,
        ms.product_type,
        ms.monthly_units_sold,
        ms.monthly_revenue,
        ms.avg_selling_price,
        mim.total_ingredient_cost,
        mim.gross_margin,
        mim.gross_margin_pct,
        ms.monthly_units_sold * mim.gross_margin as monthly_gross_profit,
        lag(mim.gross_margin_pct) over (
            partition by ms.product_id
            order by ms.sale_month
        ) as prev_month_margin_pct,
        mim.gross_margin_pct - coalesce(
            lag(mim.gross_margin_pct) over (
                partition by ms.product_id
                order by ms.sale_month
            ), mim.gross_margin_pct
        ) as margin_pct_change

    from monthly_sales as ms
    inner join menu_items as mi
        on ms.product_id = mi.product_id
    inner join menu_item_margin as mim
        on mi.menu_item_id = mim.menu_item_id

)

select * from with_margin
