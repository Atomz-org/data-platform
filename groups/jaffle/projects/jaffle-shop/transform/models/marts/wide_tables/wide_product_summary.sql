with

oi as (
    select * from {{ ref('order_items') }}
),

o as (
    select * from {{ ref('orders') }}
),

menu_items as (

    select * from {{ ref('dim_menu_items') }}

),

product_sales as (

    select
        product_id,
        sum(units_sold) as total_units_sold,
        sum(daily_revenue) as total_gross_sales,
        count(distinct sale_date) as active_sale_days,
        min(sale_date) as first_sale_date,
        max(sale_date) as last_sale_date,
        avg(units_sold) as avg_daily_units,
        avg(daily_revenue) as avg_daily_revenue

    from {{ ref('fct_product_sales') }}
    group by product_id

),

product_sales_by_store as (

    select
        product_id,
        count(distinct location_id) as stores_selling

    from {{ ref('int_product_sales_by_location') }}
    group by product_id

),

item_margin as (

    select * from {{ ref('int_menu_item_margin') }}

),

review_summary as (

    select * from {{ ref('int_product_review_summary') }}

),

popularity as (

    select * from {{ ref('int_menu_item_popularity_rank') }}

),

seasonal as (

    select
        product_id,
        max(case when season_rank = 1 then season_name end) as peak_season,
        max(case when season_rank = 1 then total_revenue end) as peak_season_revenue

    from (
        select
            product_id,
            season_name,
            total_revenue,
            row_number() over (partition by product_id order by total_revenue desc) as season_rank
        from {{ ref('int_seasonal_sales_pattern') }}
    ) as ranked
    group by product_id

),

products_base as (

    select * from {{ ref('stg_products') }}

),

-- Supply cost per product
supply_costs as (

    select
        product_id,
        avg(supply_cost) as avg_supply_cost_per_unit,
        sum(supply_cost) as total_supply_cost

    from {{ ref('order_items') }}
    group by product_id

),

-- Order frequency
order_frequency as (

    select
        oi.product_id,
        count(distinct oi.order_id) as total_orders_containing,
        count(distinct o.customer_id) as unique_customers_purchasing

    from oi
    inner join o
        on oi.order_id = o.order_id
    group by oi.product_id

)

select
    -- Product identity
    mi.menu_item_id,
    mi.menu_item_name,
    mi.menu_category_id as category_id,
    pb.product_type,
    pb.product_description,
    mi.menu_item_price as current_price,
    mi.is_available as is_active,
    pb.is_food_item,
    pb.is_drink_item,

    -- Sales volume
    ps.total_units_sold,
    ps.total_gross_sales,
    ps.active_sale_days,
    ps.first_sale_date,
    ps.last_sale_date,
    ps.avg_daily_units,
    ps.avg_daily_revenue,
    coalesce(psbs.stores_selling, 0) as stores_selling,

    -- Cost and margin
    im.gross_margin as unit_margin,
    im.gross_margin_pct as margin_pct,
    coalesce(sc.avg_supply_cost_per_unit, 0) as avg_supply_cost_per_unit,
    coalesce(sc.total_supply_cost, 0) as total_supply_cost,
    ps.total_gross_sales - coalesce(sc.total_supply_cost, 0) as total_gross_profit,
    case
        when ps.total_gross_sales > 0
        then (ps.total_gross_sales - coalesce(sc.total_supply_cost, 0)) * 100.0 / ps.total_gross_sales
        else 0
    end as gross_profit_margin_pct,

    -- Reviews
    rs.avg_rating,
    rs.total_review_count as total_reviews,

    -- Popularity and ranking
    rank() over (order by ps.total_gross_sales desc) as sales_rank,
    rank() over (order by ps.total_units_sold desc) as volume_rank,
    rank() over (order by im.gross_margin_pct desc nulls last) as margin_rank,
    rank() over (order by rs.avg_rating desc nulls last) as rating_rank,

    -- Customer reach
    coalesce(of_stats.total_orders_containing, 0) as total_orders_containing,
    coalesce(of_stats.unique_customers_purchasing, 0) as unique_customers_purchasing,

    -- Seasonal patterns
    sea.peak_season,
    sea.peak_season_revenue,

    -- Derived metrics
    case
        when ps.active_sale_days > 0
        then ps.total_units_sold * 1.0 / ps.active_sale_days
        else 0
    end as units_per_active_day,
    case
        when coalesce(of_stats.unique_customers_purchasing, 0) > 0
        then ps.total_units_sold * 1.0 / of_stats.unique_customers_purchasing
        else 0
    end as avg_units_per_customer,
    {{ dbt.datediff("ps.first_sale_date", "ps.last_sale_date", "day") }} as days_on_sale,
    case
        when ps.total_gross_sales is null or ps.total_gross_sales = 0 then 'no_sales'
        when rank() over (order by ps.total_gross_sales desc) <= 5 then 'top_seller'
        when rank() over (order by ps.total_gross_sales desc) <= 15 then 'strong_performer'
        when rank() over (order by ps.total_gross_sales asc) <= 5 then 'underperformer'
        else 'average'
    end as performance_tier

from menu_items as mi
left join product_sales as ps on mi.menu_item_id = ps.product_id
left join product_sales_by_store as psbs on mi.menu_item_id = psbs.product_id
left join item_margin as im on mi.menu_item_id = im.menu_item_id
left join review_summary as rs on mi.menu_item_id = rs.product_id
left join products_base as pb on mi.menu_item_id = pb.product_id
left join supply_costs as sc on mi.menu_item_id = sc.product_id
left join order_frequency as of_stats on mi.menu_item_id = of_stats.product_id
left join seasonal as sea on mi.menu_item_id = sea.product_id
