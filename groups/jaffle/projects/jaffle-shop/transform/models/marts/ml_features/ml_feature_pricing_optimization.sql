with

ps2 as (
    select * from {{ ref('fct_product_sales') }}
),

ps3 as (
    select * from {{ ref('fct_product_sales') }}
),

pc as (
    select * from {{ ref('fct_pricing_changes') }}
),

product_sales as (

    select
        product_id,
        product_name,
        current_unit_price,
        sum(units_sold) as total_units,
        sum(daily_revenue) as total_revenue,
        count(distinct sale_date) as active_sale_days
    from {{ ref('fct_product_sales') }}
    group by 1, 2, 3

),

margin as (

    select
        menu_item_name,
        menu_item_price,
        total_ingredient_cost,
        gross_margin,
        gross_margin_pct
    from {{ ref('int_menu_item_margin') }}

),

pricing_changes as (

    select
        product_id,
        product_name,
        count(*) as total_price_changes,
        avg(price_change_pct) as avg_price_change_pct,
        min(price_changed_date) as first_price_change,
        max(price_changed_date) as last_price_change
    from {{ ref('fct_pricing_changes') }}
    group by 1, 2

),

-- Estimate price elasticity from pricing changes
-- Compare volume before and after price changes
price_volume as (

    select
        pc.product_id,
        pc.price_changed_date,
        pc.old_price,
        pc.new_price,
        pc.price_change_pct,
        -- Volume in 30 days before change
        (
            select sum(ps2.units_sold)
            from ps2
            where ps2.product_id = pc.product_id
                and ps2.sale_date < pc.price_changed_date
                and ps2.sale_date >= {{ dbt.dateadd('day', -30, 'pc.price_changed_date') }}
        ) as volume_before_30d,
        -- Volume in 30 days after change
        (
            select sum(ps3.units_sold)
            from ps3
            where ps3.product_id = pc.product_id
                and ps3.sale_date >= pc.price_changed_date
                and ps3.sale_date < {{ dbt.dateadd('day', 30, 'pc.price_changed_date') }}
        ) as volume_after_30d
    from pc

),

elasticity_estimate as (

    select
        product_id,
        avg(
            case
                when price_change_pct != 0 and volume_before_30d > 0
                then ((volume_after_30d - volume_before_30d) * 1.0 / volume_before_30d)
                    / (price_change_pct / 100.0)
                else null
            end
        ) as estimated_price_elasticity
    from price_volume
    group by 1

),

features as (

    select
        ps.product_id,
        ps.product_name,
        ps.current_unit_price,
        coalesce(m.total_ingredient_cost, 0) as unit_cost,
        coalesce(m.gross_margin, 0) as unit_margin,
        coalesce(m.gross_margin_pct, 0) as margin_pct,
        ps.total_units as total_volume,
        ps.total_revenue,
        ps.active_sale_days,
        round(ps.total_units * 1.0 / nullif(ps.active_sale_days, 0), 2) as avg_daily_volume,
        coalesce(pc.total_price_changes, 0) as price_change_count,
        coalesce(pc.avg_price_change_pct, 0) as avg_price_change_pct,
        round(coalesce(ee.estimated_price_elasticity, 0), 4) as estimated_price_elasticity
    from product_sales as ps
    left join margin as m
        on ps.product_name = m.menu_item_name
    left join pricing_changes as pc
        on ps.product_id = pc.product_id
    left join elasticity_estimate as ee
        on ps.product_id = ee.product_id

)

select * from features
