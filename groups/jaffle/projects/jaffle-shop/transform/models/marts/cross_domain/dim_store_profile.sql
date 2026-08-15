select
    sb.location_id,
    sb.location_id as store_id,
    sb.location_name as store_name,

    -- Financial metrics
    coalesce(rc.total_revenue, 0) as total_revenue,
    coalesce(rc.total_expenses, 0) as total_expenses,
    coalesce(rc.total_labor_cost, 0) as total_labor_cost,
    coalesce(rc.total_net_income, 0) as total_net_income,
    round(cast(coalesce(rc.avg_operating_margin_pct, 0) as {{ dbt.type_float() }}), 2) as avg_operating_margin_pct,
    rc.months_of_data,

    -- Labor
    coalesce(lp.avg_labor_cost_pct, 0) as avg_labor_cost_pct,

    -- Inventory
    coalesce(inv.distinct_products_stocked, 0) as distinct_products_stocked,
    coalesce(inv.total_inventory_value, 0) as total_inventory_value,
    coalesce(inv.estimated_monthly_holding_cost, 0) as estimated_monthly_holding_cost,

    -- Marketing
    coalesce(mk.total_marketing_spend, 0) as total_marketing_spend,
    coalesce(mk.avg_monthly_marketing_spend, 0) as avg_monthly_marketing_spend,

    -- Staffing
    round(cast(coalesce(st.avg_staffing_ratio, 0) as {{ dbt.type_float() }}), 2) as avg_staffing_ratio,
    round(cast(coalesce(st.avg_employee_count, 0) as {{ dbt.type_float() }}), 0) as avg_employee_count

from {{ ref('stg_locations') }} as sb

left join (
    select
        location_id,
        sum(monthly_revenue) as total_revenue,
        sum(monthly_expenses) as total_expenses,
        sum(monthly_labor_cost) as total_labor_cost,
        sum(net_operating_income) as total_net_income,
        avg(operating_margin_pct) as avg_operating_margin_pct,
        count(distinct month_start) as months_of_data
    from {{ ref('int_store_revenue_costs') }}
    group by location_id
) as rc on sb.location_id = rc.location_id

left join (
    select
        location_id,
        round(cast(avg(labor_cost_pct) as {{ dbt.type_float() }}), 2) as avg_labor_cost_pct
    from {{ ref('int_store_labor_pct') }}
    group by location_id
) as lp on sb.location_id = lp.location_id

left join (
    select
        store_id,
        distinct_products_stocked,
        total_inventory_value,
        estimated_monthly_holding_cost
    from {{ ref('int_store_inventory_cost') }}
) as inv on sb.location_id = inv.store_id

left join (
    select
        store_id,
        sum(monthly_marketing_spend) as total_marketing_spend,
        round(cast(avg(monthly_marketing_spend) as {{ dbt.type_float() }}), 2) as avg_monthly_marketing_spend
    from {{ ref('int_store_marketing_spend') }}
    group by store_id
) as mk on sb.location_id = mk.store_id

left join (
    select
        location_id,
        avg(orders_per_staff) as avg_staffing_ratio,
        avg(scheduled_staff_count) as avg_employee_count
    from {{ ref('int_store_staffing_ratio') }}
    group by location_id
) as st on sb.location_id = st.location_id
