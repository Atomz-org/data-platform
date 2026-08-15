with expenses_raw as (
    select * from {{ ref('fct_expenses') }}
),

store_pnl as (
    select
        location_id,
        store_name,
        report_month,
        monthly_revenue,
        monthly_labor_cost,
        operating_expenses,
        marketing_spend,
        inventory_holding_cost,
        total_costs,
        net_profit,
        net_profit_margin_pct
    from {{ ref('rpt_store_pnl') }}
),

fixed_costs as (
    -- Approximate fixed costs from expenses (rent, equipment, insurance)
    select
        e.location_id,
        {{ dbt.date_trunc("month", "e.incurred_date") }} as expense_month,
        sum(case when e.category_name in ('rent', 'equipment', 'insurance', 'utilities')
            then e.expense_amount else 0 end) as monthly_fixed_costs,
        sum(case when e.category_name not in ('rent', 'equipment', 'insurance', 'utilities')
            then e.expense_amount else 0 end) as monthly_variable_expenses
    from expenses_raw as e
    group by e.location_id, {{ dbt.date_trunc("month", "e.incurred_date") }}
),

combined as (
    select
        sp.location_id,
        sp.store_name,
        sp.report_month,
        sp.monthly_revenue,
        coalesce(fc.monthly_fixed_costs, 0) as fixed_costs,
        sp.monthly_labor_cost + coalesce(fc.monthly_variable_expenses, 0)
            + sp.marketing_spend + sp.inventory_holding_cost as variable_costs,
        sp.monthly_revenue
            - sp.monthly_labor_cost
            - coalesce(fc.monthly_variable_expenses, 0)
            - sp.marketing_spend
            - sp.inventory_holding_cost as contribution_margin,
        case
            when sp.monthly_revenue > 0
                then (sp.monthly_revenue
                    - sp.monthly_labor_cost
                    - coalesce(fc.monthly_variable_expenses, 0)
                    - sp.marketing_spend
                    - sp.inventory_holding_cost)
                / sp.monthly_revenue
            else 0
        end as contribution_margin_ratio
    from store_pnl as sp
    left join fixed_costs as fc
        on sp.location_id = fc.location_id
        and sp.report_month = fc.expense_month
)

select
    location_id,
    store_name,
    report_month,
    monthly_revenue,
    fixed_costs,
    variable_costs,
    contribution_margin,
    round(cast(contribution_margin_ratio * 100 as {{ dbt.type_float() }}), 2) as contribution_margin_pct,
    case
        when contribution_margin_ratio > 0
            then round(cast(fixed_costs / contribution_margin_ratio as {{ dbt.type_float() }}), 2)
        else null
    end as break_even_revenue,
    case
        when contribution_margin_ratio > 0
            then round(
                (cast(monthly_revenue - (fixed_costs / contribution_margin_ratio) as {{ dbt.type_float() }})), 2
            )
        else null
    end as margin_of_safety,
    case
        when contribution_margin_ratio > 0 and monthly_revenue > 0
            then round(
                (monthly_revenue - (fixed_costs / contribution_margin_ratio))
                / monthly_revenue * 100, 2
            )
        else null
    end as margin_of_safety_pct,
    case
        when contribution_margin_ratio > 0
            and monthly_revenue >= fixed_costs / contribution_margin_ratio
            then 'above_break_even'
        when contribution_margin_ratio > 0
            then 'below_break_even'
        else 'negative_contribution'
    end as break_even_status
from combined
