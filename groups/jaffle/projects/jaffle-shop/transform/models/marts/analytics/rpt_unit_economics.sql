with

gross_margin as (

    select * from {{ ref('int_gross_margin_by_product') }}

),

product_sales as (

    select
        product_id,
        sum(units_sold) as units_sold,
        sum(daily_revenue) as daily_revenue
    from {{ ref('fct_product_sales') }}
    group by 1

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
        coalesce(ps.daily_revenue, 0) as daily_revenue,
        gm.avg_revenue_per_unit as revenue_per_unit,
        gm.cogs_per_unit,
        gm.gross_margin_per_unit,
        coalesce(gm.total_cogs, 0) as total_cogs,
        coalesce(gm.gross_margin, 0) as total_gross_margin,
        case
            when coalesce(ps.daily_revenue, 0) > 0
                then round(cast(gm.gross_margin * 100.0 / ps.daily_revenue as {{ dbt.type_float() }}), 2)
            else 0
        end as gross_margin_pct,
        case
            when gm.gross_margin_per_unit > 3 then 'high_contribution'
            when gm.gross_margin_per_unit > 1 then 'moderate_contribution'
            else 'low_contribution'
        end as contribution_tier
    from products as p
    left join product_sales as ps
        on p.product_id = ps.product_id
    left join gross_margin as gm
        on p.product_id = gm.product_id

)

select * from final
