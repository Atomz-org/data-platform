{{
    config(
        materialized='incremental',
        unique_key='timecard_id'
    )
}}

with

timecards as (

    select * from {{ ref('stg_timecards') }}
    {% if is_incremental() %}
    where clock_in > (select max(clock_in) from {{ this }})
    {% endif %}

)

select
    timecard_id,
    employee_id,
    location_id,
    clock_in,
    clock_out,
    hours_worked,
    break_minutes,
    {{ dbt.date_trunc('day', 'clock_in') }} as work_date,
    {{ dbt.date_trunc('month', 'clock_in') }} as work_month

from timecards
