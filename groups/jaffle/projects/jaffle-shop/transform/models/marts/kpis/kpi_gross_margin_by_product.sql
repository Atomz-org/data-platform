with 
ps as (
    select * from {{ ref('int_product_sales_by_location') }}
),

rc as (
    select * from {{ ref('int_total_cost_of_goods') }}
),

final as (
    select
        ps.product_id,
        {{ dbt.date_trunc('month', 'ps.sale_date') }} as sale_month,
        sum(ps.daily_revenue) as revenue,
        sum(ps.units_sold * coalesce(rc.total_cogs_per_unit, 0)) as cogs,
        sum(ps.daily_revenue) - sum(ps.units_sold * coalesce(rc.total_cogs_per_unit, 0)) as gross_profit,
        round((sum(ps.daily_revenue) - sum(ps.units_sold * coalesce(rc.total_cogs_per_unit, 0))) * 100.0
            / nullif(sum(ps.daily_revenue), 0), 2) as gross_margin_pct
    from ps
    left join rc on cast(ps.product_id as {{ dbt.type_string() }}) = cast(rc.product_id as {{ dbt.type_string() }})
    group by 1, 2
)
select * from final
