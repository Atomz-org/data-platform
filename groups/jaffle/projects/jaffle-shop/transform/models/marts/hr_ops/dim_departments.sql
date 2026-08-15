with

departments as (

    select * from {{ ref('stg_departments') }}

),

final as (

    select
        department_id,
        department_name,
        department_description

    from departments

)

select * from final
