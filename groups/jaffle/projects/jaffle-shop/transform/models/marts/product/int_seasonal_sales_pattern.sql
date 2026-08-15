with

product_sales_daily as (

    select * from {{ ref('int_product_sales_daily') }}

),

seasonal_menus as (

    select * from {{ ref('stg_seasonal_menus') }}

),

menu_items as (

    select * from {{ ref('stg_menu_items') }}

),

seasonal_product_map as (

    select
        sm.seasonal_menu_id,
        sm.season_name,
        sm.promotion_name,
        sm.promotion_start_date,
        sm.promotion_end_date,
        mi.product_id

    from seasonal_menus as sm
    inner join menu_items as mi
        on sm.menu_item_id = mi.menu_item_id

),

sales_with_season as (

    select
        psd.sale_date,
        psd.product_id,
        psd.product_name,
        psd.units_sold,
        psd.daily_revenue,
        spm.seasonal_menu_id,
        spm.season_name,
        spm.promotion_name,
        spm.promotion_start_date,
        spm.promotion_end_date,
        case
            when spm.seasonal_menu_id is not null then true
            else false
        end as is_during_promotion

    from product_sales_daily as psd
    left join seasonal_product_map as spm
        on psd.product_id = spm.product_id
        and psd.sale_date >= spm.promotion_start_date
        and psd.sale_date <= spm.promotion_end_date

),

seasonal_summary as (

    select
        product_id,
        product_name,
        season_name,
        promotion_name,
        promotion_start_date,
        promotion_end_date,
        is_during_promotion,
        sum(units_sold) as total_units_sold,
        sum(daily_revenue) as total_revenue,
        avg(units_sold) as avg_daily_units,
        count(distinct sale_date) as active_days

    from sales_with_season
    group by
        product_id,
        product_name,
        season_name,
        promotion_name,
        promotion_start_date,
        promotion_end_date,
        is_during_promotion

)

select * from seasonal_summary
