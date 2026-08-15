select
    sn.location_name as store_name,
    rc.location_id,
    rc.report_month,
    rc.monthly_revenue,

    -- Cost breakdown
    rc.monthly_labor_cost,
    rc.monthly_expenses as operating_expenses,
    coalesce(ms.monthly_marketing_spend, 0) as marketing_spend,
    coalesce(ic.estimated_monthly_holding_cost, 0) as inventory_holding_cost,

    -- Total costs
    rc.monthly_labor_cost
        + rc.monthly_expenses
        + coalesce(ms.monthly_marketing_spend, 0)
        + coalesce(ic.estimated_monthly_holding_cost, 0) as total_costs,

    -- Profit
    rc.monthly_revenue
        - rc.monthly_labor_cost
        - rc.monthly_expenses
        - coalesce(ms.monthly_marketing_spend, 0)
        - coalesce(ic.estimated_monthly_holding_cost, 0) as net_profit,

    -- Margins
    case
        when rc.monthly_revenue > 0
            then round(
                (rc.monthly_revenue
                    - rc.monthly_labor_cost
                    - rc.monthly_expenses
                    - coalesce(ms.monthly_marketing_spend, 0)
                    - coalesce(ic.estimated_monthly_holding_cost, 0))
                / rc.monthly_revenue * 100, 2
            )
        else 0
    end as net_profit_margin_pct,

    -- Cost ratios
    case
        when rc.monthly_revenue > 0
            then round(cast(rc.monthly_labor_cost as {{ dbt.type_float() }}) / rc.monthly_revenue * 100, 2)
        else 0
    end as labor_cost_ratio_pct,
    case
        when rc.monthly_revenue > 0
            then round(cast(rc.monthly_expenses as {{ dbt.type_float() }}) / rc.monthly_revenue * 100, 2)
        else 0
    end as opex_ratio_pct,
    case
        when rc.monthly_revenue > 0
            then round(cast(coalesce(ms.monthly_marketing_spend, 0) as {{ dbt.type_float() }}) / rc.monthly_revenue * 100, 2)
        else 0
    end as marketing_ratio_pct

from (
    select
        location_id,
        month_start as report_month,
        monthly_revenue,
        monthly_expenses,
        monthly_labor_cost,
        net_operating_income,
        operating_margin_pct
    from {{ ref('int_store_revenue_costs') }}
) as rc

left join (
    select store_id, spend_month, monthly_marketing_spend
    from {{ ref('int_store_marketing_spend') }}
) as ms
    on rc.location_id = ms.store_id
    and rc.report_month = ms.spend_month

left join (
    select store_id, estimated_monthly_holding_cost
    from {{ ref('int_store_inventory_cost') }}
) as ic
    on rc.location_id = ic.store_id

left join (
    select location_id, location_name
    from {{ ref('stg_locations') }}
) as sn
    on rc.location_id = sn.location_id
