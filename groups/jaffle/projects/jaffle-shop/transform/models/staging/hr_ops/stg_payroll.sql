with

source as (

    select * from {{ source('hr_ops', 'raw_payroll') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as payroll_id,
        cast(employee_id as varchar) as employee_id,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'pay_period_start') }} as pay_period_start,
        {{ dbt.date_trunc('day', 'pay_period_end') }} as pay_period_end,
        {{ dbt.date_trunc('day', 'pay_date') }} as pay_date,

        ---------- numerics
        hours_worked as payroll_hours,
        overtime_hours as payroll_overtime_hours,
        {{ cents_to_dollars('gross_pay') }} as gross_pay,
        {{ cents_to_dollars('deductions') }} as deductions,
        {{ cents_to_dollars('net_pay') }} as net_pay

    from source

)

select * from renamed
