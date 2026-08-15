with

source as (

    select * from {{ source('hr_ops', 'raw_equipment') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as equipment_id,
        cast(store_id as varchar) as location_id,

        ---------- text
        name as equipment_name,
        type as equipment_type,
        manufacturer,
        model_number,
        serial_number,
        status as equipment_status,

        ---------- numerics
        {{ cents_to_dollars('purchase_cost') }} as purchase_cost,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'purchase_date') }} as purchase_date,
        {{ dbt.date_trunc('day', 'warranty_expiry') }} as warranty_expiry_date,
        {{ dbt.date_trunc('day', 'last_maintenance_date') }} as last_maintenance_date

    from source

)

select * from renamed
