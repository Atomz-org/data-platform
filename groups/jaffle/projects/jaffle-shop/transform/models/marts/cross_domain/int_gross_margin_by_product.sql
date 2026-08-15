with product_revenue as (
    select
        product_id,
        sum(units_sold) as units_sold,
        sum(daily_revenue) as daily_revenue,
        case
            when sum(units_sold) > 0
                then sum(daily_revenue) / sum(units_sold)
            else 0
        end as avg_revenue_per_unit
    from {{ ref('fct_product_sales') }}
    group by product_id
),

cogs as (
    select
        product_id,
        total_cogs_per_unit
    from {{ ref('int_total_cost_of_goods') }}
)

select
    pr.product_id,
    pr.units_sold,
    pr.daily_revenue,
    pr.avg_revenue_per_unit,
    coalesce(c.total_cogs_per_unit, 0) as cogs_per_unit,
    pr.units_sold * coalesce(c.total_cogs_per_unit, 0) as total_cogs,
    pr.daily_revenue - (pr.units_sold * coalesce(c.total_cogs_per_unit, 0)) as gross_margin,
    pr.avg_revenue_per_unit - coalesce(c.total_cogs_per_unit, 0) as gross_margin_per_unit,
    case
        when pr.daily_revenue > 0
            then round(
                (pr.daily_revenue - (pr.units_sold * coalesce(c.total_cogs_per_unit, 0)))
                / pr.daily_revenue * 100, 2
            )
        else 0
    end as gross_margin_pct
from product_revenue as pr
left join cogs as c
    on pr.product_id = c.product_id
