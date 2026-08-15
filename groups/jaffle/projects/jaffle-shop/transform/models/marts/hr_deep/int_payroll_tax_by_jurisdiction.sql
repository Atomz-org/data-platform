with

payroll as (

    select * from {{ ref('stg_payroll') }}

),

employees as (

    select
        employee_id,
        location_id
    from {{ ref('stg_employees') }}

),

locations as (

    select
        location_id,
        location_name
    from {{ ref('stg_locations') }}

),

final as (

    select
        l.location_id,
        l.location_name,
        {{ dbt.date_trunc('month', 'p.pay_date') }} as payroll_month,
        count(distinct p.employee_id) as employee_count,
        sum(p.gross_pay) as total_gross_pay,
        sum(p.deductions) as total_deductions,
        sum(p.net_pay) as total_net_pay,
        case
            when sum(p.gross_pay) > 0
                then round(cast(sum(p.deductions) * 100.0 / sum(p.gross_pay) as {{ dbt.type_float() }}), 2)
            else 0
        end as effective_deduction_rate_pct,
        avg(p.gross_pay) as avg_gross_pay
    from payroll as p
    inner join employees as e
        on p.employee_id = e.employee_id
    inner join locations as l
        on e.location_id = l.location_id
    group by 1, 2, 3

)

select * from final
