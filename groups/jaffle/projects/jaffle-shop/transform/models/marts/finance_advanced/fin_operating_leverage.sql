with

expenses as (

    select
        location_id,
        location_name,
        {{ dbt.date_trunc('month', 'incurred_date') }} as expense_month,
        category_name,
        is_cost_of_goods_sold,
        expense_amount,
        case
            when category_name in ('rent', 'insurance', 'depreciation', 'licenses') then 'fixed'
            when is_cost_of_goods_sold then 'variable'
            when category_name in ('utilities', 'maintenance') then 'semi_variable'
            else 'variable'
        end as cost_type
    from {{ ref('fct_expenses') }}

),

monthly_summary as (

    select
        location_id,
        location_name,
        expense_month,
        sum(case when cost_type = 'fixed' then expense_amount else 0 end) as fixed_costs,
        sum(case when cost_type = 'variable' then expense_amount else 0 end) as variable_costs,
        sum(case when cost_type = 'semi_variable' then expense_amount else 0 end) as semi_variable_costs,
        sum(expense_amount) as total_costs
    from expenses
    group by 1, 2, 3

),

final as (

    select
        location_id,
        location_name,
        expense_month,
        fixed_costs,
        variable_costs,
        semi_variable_costs,
        total_costs,
        case
            when total_costs > 0
            then fixed_costs / total_costs * 100
            else 0
        end as fixed_cost_pct,
        case
            when total_costs > 0
            then variable_costs / total_costs * 100
            else 0
        end as variable_cost_pct,
        -- Higher ratio = more operating leverage
        case
            when variable_costs > 0
            then fixed_costs / variable_costs
            else null
        end as operating_leverage_ratio
    from monthly_summary

)

select * from final
