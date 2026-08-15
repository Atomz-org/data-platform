with 

store_pnl as (
    select * from {{ ref('rpt_store_pnl') }}
),

product_sales_by_loc as (
    select * from {{ ref('int_product_sales_by_location') }}
),

cogs_data as (
    select * from {{ ref('int_total_cost_of_goods') }}
),

store_food_cost as (
    select
        location_id,
        store_name,
        report_month,
        monthly_revenue,
        total_costs
    from store_pnl
),

cogs_by_store as (
    select
        psl.location_id,
        {{ dbt.date_trunc("month", "psl.sale_date") }} as sale_month,
        sum(psl.units_sold * coalesce(cogs.total_cogs_per_unit, 0)) as monthly_cogs
    from product_sales_by_loc as psl
    left join cogs_data as cogs
        on psl.product_id = cogs.product_id
    group by psl.location_id, {{ dbt.date_trunc("month", "psl.sale_date") }}
),

food_cost_pct as (
    select
        sfc.location_id,
        sfc.store_name,
        sfc.report_month,
        sfc.monthly_revenue,
        coalesce(cbs.monthly_cogs, 0) as monthly_cogs,
        case
            when sfc.monthly_revenue > 0
            then round(coalesce(cbs.monthly_cogs, 0) * 100.0 / sfc.monthly_revenue, 2)
            else 0
        end as food_cost_pct
    from store_food_cost as sfc
    left join cogs_by_store as cbs
        on sfc.location_id = cbs.location_id
        and sfc.report_month = cbs.sale_month
),

fleet_avg as (
    select avg(food_cost_pct) as fleet_avg_food_cost_pct
    from food_cost_pct
),

final as (
    select
        fcp.*,
        fa.fleet_avg_food_cost_pct,
        fcp.food_cost_pct - fa.fleet_avg_food_cost_pct as variance_from_fleet,
        case
            when fcp.food_cost_pct > fa.fleet_avg_food_cost_pct * 1.2 then 'critical'
            when fcp.food_cost_pct > fa.fleet_avg_food_cost_pct * 1.1 then 'warning'
            else 'normal'
        end as alert_level
    from food_cost_pct as fcp
    cross join fleet_avg as fa
)

select * from final
