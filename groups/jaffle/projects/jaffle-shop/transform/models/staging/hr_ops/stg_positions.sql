with

source as (

    select * from {{ source('hr_ops', 'raw_positions') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as position_id,
        cast(department_id as varchar) as department_id,

        ---------- text
        title as position_title,
        pay_grade,

        ---------- numerics
        {{ cents_to_dollars('min_pay_rate') }} as min_hourly_rate,
        {{ cents_to_dollars('max_pay_rate') }} as max_hourly_rate,

        ---------- booleans
        is_management

    from source

)

select * from renamed
