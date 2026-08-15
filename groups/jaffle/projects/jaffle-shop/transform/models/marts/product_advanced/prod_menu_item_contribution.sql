with

sales as (

    select
        product_id,
        sum(units_sold) as total_qty,
        sum(daily_revenue) as daily_revenue
    from {{ ref('fct_product_sales') }}
    group by 1

),

margins as (

    select menu_item_id as product_id, gross_margin, gross_margin_pct
    from {{ ref('int_menu_item_margin') }}

),

products as (

    select product_id, product_name, product_type
    from {{ ref('stg_products') }}

),

final as (

    select
        s.product_id,
        p.product_name,
        p.product_type,
        s.total_qty,
        s.daily_revenue,
        coalesce(m.gross_margin, 0) * s.total_qty as total_margin_contribution,
        coalesce(m.gross_margin_pct, 0) as gross_margin_pct,
        cast(s.daily_revenue as {{ dbt.type_float() }})
            / nullif(sum(s.daily_revenue) over (), 0) * 100 as revenue_contribution_pct,
        cast(coalesce(m.gross_margin, 0) * s.total_qty as {{ dbt.type_float() }})
            / nullif(sum(coalesce(m.gross_margin, 0) * s.total_qty) over (), 0) * 100 as profit_contribution_pct,
        rank() over (order by s.daily_revenue desc) as revenue_rank,
        rank() over (order by coalesce(m.gross_margin, 0) * s.total_qty desc) as profit_rank
    from sales as s
    inner join products as p on s.product_id = p.product_id
    left join margins as m on s.product_id = m.product_id

)

select * from final
