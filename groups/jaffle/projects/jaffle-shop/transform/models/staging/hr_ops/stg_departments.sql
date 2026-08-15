with

source as (

    select * from {{ source('hr_ops', 'raw_departments') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as department_id,

        ---------- text
        name as department_name,
        description as department_description

    from source

)

select * from renamed
