{{
    config(
        materialized='incremental',
        unique_key='waste_event_id'
    )
}}

with

waste_logs as (

    select * from {{ ref('stg_waste_logs') }}
    {% if is_incremental() %}
    where wasted_at > (select max(wasted_at) from {{ this }})
    {% endif %}

)

select
    waste_log_id as waste_event_id,
    product_id,
    location_id,
    wasted_at,
    quantity_wasted,
    waste_reason,
    cost_of_waste,
    {{ dbt.date_trunc('month', 'wasted_at') }} as waste_month

from waste_logs
