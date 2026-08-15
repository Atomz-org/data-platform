with

product_viability as (
    select * from {{ ref('scr_product_viability') }}
),

product_sales as (
    select
        product_id,
        sum(units_sold) as units_sold,
        sum(daily_revenue) as total_revenue
    from {{ ref('fct_product_sales') }}
    group by 1
),

margins as (
    select
        menu_item_id as product_id,
        gross_margin,
        gross_margin_pct
    from {{ ref('int_menu_item_margin') }}
),

products as (
    select
        product_id,
        product_name,
        product_type
    from {{ ref('stg_products') }}
),

final as (
    select
        p.product_id,
        p.product_name,
        p.product_type,
        coalesce(ps.units_sold, 0) as units_sold,
        coalesce(ps.total_revenue, 0) as total_revenue,
        m.gross_margin,
        m.gross_margin_pct,
        pv.viability_score,
        pv.viability_tier,
        case
            when coalesce(ps.total_revenue, 0) > 0 and m.gross_margin_pct > 50 then 'star'
            when coalesce(ps.total_revenue, 0) > 0 and m.gross_margin_pct <= 50 then 'cash_cow'
            when coalesce(ps.total_revenue, 0) = 0 then 'dog'
            else 'question_mark'
        end as portfolio_quadrant
    from products as p
    left join product_sales as ps on p.product_id = ps.product_id
    left join margins as m on p.product_id = m.product_id
    left join product_viability as pv on p.product_id = pv.product_id
)

select * from final
