with

seasonal_sales_pattern as (

    select * from {{ ref('int_seasonal_sales_pattern') }}

),

dim_menu_items as (

    select * from {{ ref('dim_menu_items') }}

),

-- Separate seasonal and permanent items
seasonal_items as (

    select
        ssp.product_id,
        ssp.product_name,
        dmi.is_seasonal,
        dmi.category_name,
        dmi.menu_item_price,
        ssp.season_name,
        ssp.promotion_name,
        ssp.promotion_start_date,
        ssp.promotion_end_date,
        ssp.is_during_promotion,
        ssp.total_units_sold,
        ssp.total_revenue,
        ssp.avg_daily_units,
        ssp.active_days

    from seasonal_sales_pattern as ssp
    inner join dim_menu_items as dmi
        on ssp.product_id = dmi.product_id

),

-- Compare seasonal vs permanent during same periods
seasonal_summary as (

    select
        product_id,
        product_name,
        is_seasonal,
        category_name,
        menu_item_price,
        season_name,
        promotion_name,
        sum(case when is_during_promotion then total_units_sold else 0 end) as promo_units_sold,
        sum(case when is_during_promotion then total_revenue else 0 end) as promo_revenue,
        sum(case when is_during_promotion then avg_daily_units else 0 end) as promo_avg_daily_units,
        sum(case when not is_during_promotion then total_units_sold else 0 end) as non_promo_units_sold,
        sum(case when not is_during_promotion then total_revenue else 0 end) as non_promo_revenue,
        sum(case when not is_during_promotion then avg_daily_units else 0 end) as non_promo_avg_daily_units,
        sum(total_units_sold) as total_units_sold,
        sum(total_revenue) as total_revenue

    from seasonal_items
    group by
        product_id,
        product_name,
        is_seasonal,
        category_name,
        menu_item_price,
        season_name,
        promotion_name

),

final as (

    select
        *,
        case
            when non_promo_avg_daily_units > 0
            then (promo_avg_daily_units - non_promo_avg_daily_units)
                 / non_promo_avg_daily_units * 100
            else null
        end as promotion_lift_pct,
        case
            when is_seasonal and promo_units_sold > 0 then 'seasonal_active'
            when is_seasonal and promo_units_sold = 0 then 'seasonal_dormant'
            when not is_seasonal and promo_units_sold > 0 then 'permanent_with_promotion'
            else 'permanent_baseline'
        end as item_promotion_status,
        -- Revenue per day comparison
        case
            when promo_avg_daily_units > non_promo_avg_daily_units * 1.2
            then 'outperforms_during_promotion'
            when promo_avg_daily_units < non_promo_avg_daily_units * 0.8
            then 'underperforms_during_promotion'
            else 'consistent_performance'
        end as promotion_performance

    from seasonal_summary

)

select * from final
