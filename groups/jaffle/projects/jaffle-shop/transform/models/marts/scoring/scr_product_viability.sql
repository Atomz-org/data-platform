with

product_sales as (

    select
        product_id,
        product_name,
        product_type,
        sum(units_sold) as total_units_sold,
        sum(daily_revenue) as total_revenue,
        count(distinct sale_date) as active_sale_days,
        max(sale_date) as last_sale_date
    from {{ ref('fct_product_sales') }}
    group by product_id, product_name, product_type

),

margins as (

    select
        menu_item_id as product_id,
        gross_margin_pct
    from {{ ref('int_menu_item_margin') }}

),

reviews as (

    select * from {{ ref('int_product_review_summary') }}

),

inventory as (

    select
        product_id,
        sum(current_quantity) as total_inventory_on_hand
    from {{ ref('int_inventory_current_level') }}
    group by product_id

),

scored as (

    select
        ps.product_id,
        ps.product_name,
        ps.product_type,
        ps.total_units_sold,
        ps.total_revenue,
        ps.active_sale_days,

        -- Sales trend component (0-25): more sales = better
        case
            when ps.total_units_sold >= 500 then 25
            when ps.total_units_sold >= 200 then 20
            when ps.total_units_sold >= 100 then 15
            when ps.total_units_sold >= 50 then 8
            else 3
        end as sales_score,

        -- Margin component (0-25)
        case
            when coalesce(m.gross_margin_pct, 0) >= 70 then 25
            when coalesce(m.gross_margin_pct, 0) >= 50 then 20
            when coalesce(m.gross_margin_pct, 0) >= 30 then 15
            when coalesce(m.gross_margin_pct, 0) >= 10 then 8
            else 0
        end as margin_score,

        -- Review rating component (0-25)
        case
            when coalesce(r.avg_rating, 0) >= 4.5 then 25
            when coalesce(r.avg_rating, 0) >= 4.0 then 20
            when coalesce(r.avg_rating, 0) >= 3.5 then 15
            when coalesce(r.avg_rating, 0) >= 3.0 then 8
            else 3
        end as review_score,

        -- Inventory availability component (0-25)
        case
            when coalesce(inv.total_inventory_on_hand, 0) >= 100 then 25
            when coalesce(inv.total_inventory_on_hand, 0) >= 50 then 20
            when coalesce(inv.total_inventory_on_hand, 0) >= 20 then 15
            when coalesce(inv.total_inventory_on_hand, 0) > 0 then 8
            else 0
        end as availability_score,

        -- Raw metrics
        coalesce(m.gross_margin_pct, 0) as gross_margin_pct,
        coalesce(r.avg_rating, 0) as avg_review_rating,
        coalesce(r.total_review_count, 0) as total_reviews,
        coalesce(inv.total_inventory_on_hand, 0) as inventory_on_hand

    from product_sales as ps

    left join margins as m
        on ps.product_id = m.product_id

    left join reviews as r
        on ps.product_id = r.product_id

    left join inventory as inv
        on ps.product_id = inv.product_id

),

final as (

    select
        *,
        sales_score + margin_score + review_score + availability_score as viability_score,
        case
            when sales_score + margin_score + review_score + availability_score >= 80 then 'star'
            when sales_score + margin_score + review_score + availability_score >= 60 then 'healthy'
            when sales_score + margin_score + review_score + availability_score >= 40 then 'watch'
            else 'at_risk'
        end as viability_tier

    from scored

)

select * from final
