with

seasonal_sales_pattern as (

    select * from {{ ref('int_seasonal_sales_pattern') }}

),

during_promo as (

    select
        product_id,
        product_name,
        season_name,
        promotion_name,
        promotion_start_date,
        promotion_end_date,
        total_units_sold as promo_units_sold,
        total_revenue as promo_revenue,
        avg_daily_units as promo_avg_daily_units,
        active_days as promo_active_days

    from seasonal_sales_pattern
    where is_during_promotion = true

),

outside_promo as (

    select
        product_id,
        avg_daily_units as baseline_avg_daily_units,
        total_units_sold as baseline_total_units

    from seasonal_sales_pattern
    where is_during_promotion = false

),

final as (

    select
        dp.product_id,
        dp.product_name,
        dp.season_name,
        dp.promotion_name,
        dp.promotion_start_date,
        dp.promotion_end_date,
        dp.promo_active_days,
        dp.promo_units_sold,
        dp.promo_revenue,
        dp.promo_avg_daily_units,
        op.baseline_avg_daily_units,
        case
            when coalesce(op.baseline_avg_daily_units, 0) > 0
            then (dp.promo_avg_daily_units - op.baseline_avg_daily_units)
                 / op.baseline_avg_daily_units * 100
            else null
        end as sales_lift_pct,
        case
            when dp.promo_avg_daily_units > coalesce(op.baseline_avg_daily_units, 0) * 1.2
            then 'strong_lift'
            when dp.promo_avg_daily_units > coalesce(op.baseline_avg_daily_units, 0)
            then 'moderate_lift'
            else 'no_lift'
        end as promotion_effectiveness

    from during_promo as dp
    left join outside_promo as op
        on dp.product_id = op.product_id

)

select * from final
