with

source as (

    select * from {{ source('hr_ops', 'raw_maintenance_logs') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as maintenance_log_id,
        cast(equipment_id as varchar) as equipment_id,
        cast(performed_by as varchar) as technician_id,

        ---------- text
        maintenance_type,
        description as maintenance_description,
        status as maintenance_status,

        ---------- numerics
        {{ cents_to_dollars('cost') }} as maintenance_cost,
        downtime_hours,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'scheduled_date') }} as scheduled_date,
        {{ dbt.date_trunc('day', 'completed_date') }} as completed_date

    from source

)

select * from renamed
