with

source as (

    select * from {{ source('hr_ops', 'raw_employees') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as employee_id,
        cast(store_id as varchar) as location_id,
        cast(department_id as varchar) as department_id,
        cast(position_id as varchar) as position_id,

        ---------- text
        first_name,
        last_name,
        first_name || ' ' || last_name as full_name,
        email,
        employment_status,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'hire_date') }} as hire_date,
        {{ dbt.date_trunc('day', 'termination_date') }} as termination_date

    from source

)

select * from renamed
