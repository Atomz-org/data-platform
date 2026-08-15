{{
    config(
        materialized='incremental',
        unique_key='movement_id'
    )
}}

with

movements as (

    select * from {{ ref('stg_inventory_movements') }}
    {% if is_incremental() %}
    where moved_at > (select max(moved_at) from {{ this }})
    {% endif %}

)

select
    movement_id,
    product_id,
    location_id,
    movement_type,
    quantity,
    moved_at,
    {{ dbt.date_trunc('month', 'moved_at') }} as movement_month

from movements
