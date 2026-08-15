with

seasonal_menus as (

    select * from {{ ref('stg_seasonal_menus') }}

),

product_sales as (

    select
        product_id,
        sum(units_sold) as units_sold,
        sum(daily_revenue) as daily_revenue
    from {{ ref('fct_product_sales') }}
    group by 1

),

menu_items as (

    select
        menu_item_id,
        product_id,
        menu_item_name,
        is_seasonal
    from {{ ref('stg_menu_items') }}

),

seasonal_performance as (

    select
        sm.seasonal_menu_id,
        sm.season_name,
        sm.promotion_name,
        sm.promotion_start_date,
        sm.promotion_end_date,
        sm.is_active_promotion,
        mi.product_id,
        mi.menu_item_name,
        coalesce(ps.units_sold, 0) as units_sold,
        coalesce(ps.daily_revenue, 0) as daily_revenue
    from seasonal_menus as sm
    inner join menu_items as mi
        on sm.menu_item_id = mi.menu_item_id
    left join product_sales as ps
        on mi.product_id = ps.product_id

),

final as (

    select
        season_name,
        promotion_name,
        count(distinct product_id) as product_count,
        sum(units_sold) as units_sold,
        sum(daily_revenue) as daily_revenue,
        avg(daily_revenue) as avg_revenue_per_product,
        min(promotion_start_date) as season_start,
        max(promotion_end_date) as season_end
    from seasonal_performance
    group by 1, 2

)

select * from final
