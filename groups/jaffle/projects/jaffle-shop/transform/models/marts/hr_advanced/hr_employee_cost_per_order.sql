with

labor_cost as (
    select
        employee_id,
        {{ dbt.date_trunc('month', 'pay_period_start') }} as pay_month,
        sum(gross_pay) as monthly_gross_pay
    from {{ ref('fct_payroll') }}
    group by 1, 2
),

productivity as (
    select
        employee_id,
        {{ dbt.date_trunc('month', 'work_date') }} as pay_month,
        sum(orders_handled) as orders_handled
    from {{ ref('int_employee_productivity') }}
    group by 1, 2
),

final as (
    select
        lc.employee_id,
        lc.pay_month,
        lc.monthly_gross_pay,
        coalesce(p.orders_handled, 0) as orders_handled,
        case
            when coalesce(p.orders_handled, 0) > 0
            then lc.monthly_gross_pay / p.orders_handled
            else null
        end as cost_per_order,
        case
            when coalesce(p.orders_handled, 0) > 0
            then round(lc.monthly_gross_pay / p.orders_handled, 2)
            else null
        end as labor_cost_per_order
    from labor_cost as lc
    left join productivity as p
        on lc.employee_id = p.employee_id
        and lc.pay_month = p.pay_month
)

select * from final
