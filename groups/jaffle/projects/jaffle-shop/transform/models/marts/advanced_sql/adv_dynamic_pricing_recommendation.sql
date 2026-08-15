-- adv_dynamic_pricing_recommendation.sql
-- Technique: Business rule engine using layered CASE expressions
-- Implements 10+ pricing rules that consider margin, sales velocity, price point,
-- and product type to recommend pricing actions. This pattern simulates a
-- rule-based decision engine entirely in SQL, useful when business logic is
-- too complex for simple thresholds but doesn't warrant a separate service.

with product_sales as (

    select * from {{ ref('fct_product_sales') }}

),

margins as (

    select * from {{ ref('int_menu_item_margin') }}

),

-- Aggregate sales metrics per product for velocity analysis
product_velocity as (

    select
        product_id,
        product_name,
        product_type,
        current_unit_price,
        sum(units_sold) as total_units_sold,
        sum(daily_revenue) as total_revenue,
        count(distinct sale_date) as days_with_sales,
        -- Average daily units as a velocity proxy
        case
            when count(distinct sale_date) > 0
            then sum(units_sold)::numeric / count(distinct sale_date)
            else 0
        end as avg_daily_units,
        max(sale_date) as last_sale_date,
        min(sale_date) as first_sale_date
    from product_sales
    group by 1, 2, 3, 4

),

-- Join velocity with margin data
product_analysis as (

    select
        pv.product_id,
        pv.product_name,
        pv.product_type,
        pv.current_unit_price,
        pv.total_units_sold,
        pv.total_revenue,
        pv.days_with_sales,
        pv.avg_daily_units,
        pv.last_sale_date,
        pv.first_sale_date,
        m.gross_margin,
        m.gross_margin_pct,
        m.total_ingredient_cost,

        -- Classify velocity into tiers
        case
            when pv.avg_daily_units >= 10 then 'high'
            when pv.avg_daily_units >= 3 then 'medium'
            else 'low'
        end as velocity_tier,

        -- Classify margin into tiers
        case
            when m.gross_margin_pct >= 60 then 'high'
            when m.gross_margin_pct >= 35 then 'medium'
            when m.gross_margin_pct >= 20 then 'low'
            else 'critical'
        end as margin_tier

    from product_velocity as pv
    left join margins as m
        on pv.product_id = m.menu_item_id

),

-- Apply the 10+ pricing rules as layered CASE expressions
pricing_rules as (

    select
        *,

        -- Rule engine: evaluate rules in priority order (first match wins)
        case
            -- Rule 1: High margin + high velocity → reduce price to drive even more volume
            when margin_tier = 'high' and velocity_tier = 'high'
                then 'decrease_for_volume'

            -- Rule 2: High margin + medium velocity → slight discount to boost velocity
            when margin_tier = 'high' and velocity_tier = 'medium'
                then 'moderate_discount'

            -- Rule 3: High margin + low velocity → big promotional push
            when margin_tier = 'high' and velocity_tier = 'low'
                then 'promotional_push'

            -- Rule 4: Medium margin + high velocity → hold price (sweet spot)
            when margin_tier = 'medium' and velocity_tier = 'high'
                then 'hold_price'

            -- Rule 5: Medium margin + medium velocity → test small increase
            when margin_tier = 'medium' and velocity_tier = 'medium'
                then 'test_price_increase'

            -- Rule 6: Medium margin + low velocity → bundle with popular items
            when margin_tier = 'medium' and velocity_tier = 'low'
                then 'bundle_strategy'

            -- Rule 7: Low margin + high velocity → increase price (demand supports it)
            when margin_tier = 'low' and velocity_tier = 'high'
                then 'increase_price'

            -- Rule 8: Low margin + medium velocity → moderate price increase
            when margin_tier = 'low' and velocity_tier = 'medium'
                then 'moderate_increase'

            -- Rule 9: Low margin + low velocity → review for discontinuation
            when margin_tier = 'low' and velocity_tier = 'low'
                then 'review_discontinue'

            -- Rule 10: Critical margin + high velocity → urgent price increase
            when margin_tier = 'critical' and velocity_tier = 'high'
                then 'urgent_price_increase'

            -- Rule 11: Critical margin + any velocity → discontinue
            when margin_tier = 'critical' and velocity_tier in ('medium', 'low')
                then 'discontinue'

            -- Rule 12: No margin data → flag for cost review
            when gross_margin_pct is null
                then 'needs_cost_review'

            else 'no_action'
        end as pricing_recommendation,

        -- Suggested price adjustment percentage
        case
            when margin_tier = 'high' and velocity_tier = 'high' then -10.0
            when margin_tier = 'high' and velocity_tier = 'medium' then -5.0
            when margin_tier = 'high' and velocity_tier = 'low' then -15.0
            when margin_tier = 'medium' and velocity_tier = 'high' then 0.0
            when margin_tier = 'medium' and velocity_tier = 'medium' then 5.0
            when margin_tier = 'medium' and velocity_tier = 'low' then 0.0
            when margin_tier = 'low' and velocity_tier = 'high' then 15.0
            when margin_tier = 'low' and velocity_tier = 'medium' then 10.0
            when margin_tier = 'low' and velocity_tier = 'low' then 0.0
            when margin_tier = 'critical' and velocity_tier = 'high' then 25.0
            when margin_tier = 'critical' then 0.0
            else 0.0
        end as suggested_adjustment_pct,

        -- Calculate the suggested new price
        case
            when margin_tier = 'high' and velocity_tier = 'high'
                then round(current_unit_price * 0.90, 2)
            when margin_tier = 'high' and velocity_tier = 'medium'
                then round(current_unit_price * 0.95, 2)
            when margin_tier = 'high' and velocity_tier = 'low'
                then round(current_unit_price * 0.85, 2)
            when margin_tier = 'medium' and velocity_tier = 'medium'
                then round(current_unit_price * 1.05, 2)
            when margin_tier = 'low' and velocity_tier = 'high'
                then round(current_unit_price * 1.15, 2)
            when margin_tier = 'low' and velocity_tier = 'medium'
                then round(current_unit_price * 1.10, 2)
            when margin_tier = 'critical' and velocity_tier = 'high'
                then round(current_unit_price * 1.25, 2)
            else current_unit_price
        end as suggested_price,

        -- Priority for action (1 = most urgent)
        case
            when margin_tier = 'critical' then 1
            when margin_tier = 'low' and velocity_tier = 'low' then 2
            when margin_tier = 'low' then 3
            when margin_tier = 'high' and velocity_tier = 'low' then 4
            else 5
        end as action_priority

    from product_analysis

)

select
    product_id,
    product_name,
    product_type,
    current_unit_price,
    total_ingredient_cost,
    gross_margin,
    gross_margin_pct,
    total_units_sold,
    avg_daily_units,
    velocity_tier,
    margin_tier,
    pricing_recommendation,
    suggested_adjustment_pct,
    suggested_price,
    action_priority,
    days_with_sales,
    last_sale_date
from pricing_rules
order by action_priority, product_name
