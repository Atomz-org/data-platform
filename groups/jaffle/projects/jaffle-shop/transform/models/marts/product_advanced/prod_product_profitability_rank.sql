with

sales as (
    select
        product_id,
        sum(units_sold) as total_qty,
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
    select product_id, product_name, product_type
    from {{ ref('stg_products') }}
),

base_metrics as (
    select
        s.product_id,
        p.product_name,
        p.product_type,
        s.total_qty,
        s.total_revenue,
        coalesce(m.gross_margin, 0) as gross_margin,
        coalesce(m.gross_margin_pct, 0) as gross_margin_pct,
        coalesce(m.gross_margin, 0) * total_qty as total_contribution_margin,
        sum(coalesce(m.gross_margin, 0) * total_qty) over () as total_all_products_margin
    from sales as s
    inner join products as p on s.product_id = p.product_id
    left join margins as m on s.product_id = m.product_id
),

final as (
    select
        product_id,
        product_name,
        product_type,
        total_qty,
        total_revenue,
        gross_margin,
        gross_margin_pct,
        total_contribution_margin,
        rank() over (order by total_contribution_margin desc) as profitability_rank,
        total_all_products_margin,
        case
            when total_all_products_margin > 0
            then cast(total_contribution_margin as {{ dbt.type_float() }}) / total_all_products_margin * 100
            else 0
        end as profit_share_pct,
        sum(case
            when total_all_products_margin > 0
            then cast(total_contribution_margin as {{ dbt.type_float() }}) / total_all_products_margin * 100
            else 0
        end) over (order by total_contribution_margin desc) as cumulative_profit_share_pct
    from base_metrics
)

select * from final
