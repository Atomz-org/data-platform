with

inventory_turnover as (

    select * from {{ ref('rpt_inventory_turnover') }}

),

lead_times as (

    select * from {{ ref('int_lead_time_by_supplier') }}

),

waste_rates as (

    select * from {{ ref('int_waste_rate_by_product') }}

),

depletion_rates as (

    select * from {{ ref('int_stock_depletion_rate') }}

),

reorder_points as (

    select * from {{ ref('int_reorder_point_calc') }}

),

delivery_on_time as (

    select * from {{ ref('int_delivery_on_time_rate') }}

),

turnover_kpi as (

    select
        avg(inventory_turnover_ratio) as avg_inventory_turnover,
        count(
            case when current_stock > 0 then 1 end
        ) as products_in_stock,
        count(*) as total_product_locations

    from inventory_turnover

),

lead_time_kpi as (

    select
        avg(avg_lead_time_days) as overall_avg_lead_time_days,
        avg(on_time_delivery_rate) as overall_on_time_delivery_rate

    from lead_times

),

waste_kpi as (

    select
        avg(waste_rate) as avg_waste_rate,
        sum(total_cost_of_waste) as total_waste_cost,
        sum(total_quantity_wasted) as total_waste_quantity

    from waste_rates

),

fill_rate_kpi as (

    select
        count(
            case when needs_reorder = false then 1 end
        ) as items_above_reorder_point,
        count(*) as total_tracked_items,
        case
            when count(*) > 0
                then count(
                    case when needs_reorder = false then 1 end
                ) * 1.0 / count(*)
            else null
        end as fill_rate

    from reorder_points

),

delivery_kpi as (

    select
        avg(on_time_rate) as avg_supplier_on_time_rate,
        sum(total_deliveries) as total_deliveries,
        sum(on_time_deliveries) as total_on_time_deliveries

    from delivery_on_time

),

combined_kpis as (

    select
        turnover_kpi.avg_inventory_turnover,
        turnover_kpi.products_in_stock,
        turnover_kpi.total_product_locations,
        lead_time_kpi.overall_avg_lead_time_days,
        lead_time_kpi.overall_on_time_delivery_rate as po_on_time_rate,
        waste_kpi.avg_waste_rate,
        waste_kpi.total_waste_cost,
        waste_kpi.total_waste_quantity,
        fill_rate_kpi.fill_rate,
        fill_rate_kpi.items_above_reorder_point,
        fill_rate_kpi.total_tracked_items,
        delivery_kpi.avg_supplier_on_time_rate as delivery_on_time_rate,
        delivery_kpi.total_deliveries,
        delivery_kpi.total_on_time_deliveries

    from turnover_kpi
    cross join lead_time_kpi
    cross join waste_kpi
    cross join fill_rate_kpi
    cross join delivery_kpi

)

select * from combined_kpis
