with

product_sales as (

    select * from {{ ref('int_product_sales_daily') }}

),

margins as (

    select
        menu_item_id,
        menu_item_name,
        gross_margin,
        gross_margin_pct
    from {{ ref('int_menu_item_margin') }}

),

final as (

    select
        ps.sale_date,
        ps.product_id,
        ps.product_name,
        ps.product_type,
        ps.units_sold,
        ps.order_count,
        ps.daily_revenue,
        coalesce(m.gross_margin, 0) as unit_margin,
        coalesce(m.gross_margin_pct, 0) as margin_pct,
        ps.units_sold * coalesce(m.gross_margin, 0) as daily_margin

    from product_sales as ps

    left join margins as m
        on ps.product_id = m.menu_item_id

)

select * from final
