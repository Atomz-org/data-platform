{{
    config(
        materialized='incremental',
        unique_key='shift_id'
    )
}}

with

shifts as (

    select * from {{ ref('stg_shifts') }}
    {% if is_incremental() %}
    where shift_date > (select max(shift_date) from {{ this }})
    {% endif %}

)

select
    shift_id,
    employee_id,
    location_id,
    shift_date,
    scheduled_start,
    scheduled_end,
    scheduled_hours,
    {{ dbt.date_trunc('month', 'shift_date') }} as shift_month

from shifts
