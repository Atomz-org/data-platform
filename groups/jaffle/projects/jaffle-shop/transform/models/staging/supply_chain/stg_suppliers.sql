with

source as (

    select * from {{ source('supply_chain', 'raw_suppliers') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as supplier_id,

        ---------- text
        name as supplier_name,
        contact_name,
        contact_email,
        phone,
        address,
        city,
        state,
        country,

        ---------- booleans
        is_active,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'created_at') }} as created_at

    from source

)

select * from renamed
