with

waste_events as (

    select * from {{ ref('fct_waste_events') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

)

select
    we.waste_log_id,
    we.product_id,
    we.product_name,
    we.product_type,
    we.location_id,
    we.location_name as store_name,
    we.wasted_at,
    we.quantity_wasted,
    we.cost_of_waste,
    we.waste_reason,
    round(we.cost_of_waste / nullif(we.quantity_wasted, 0), 2) as cost_per_unit_wasted,
    {{ dbt.date_trunc('month', 'we.wasted_at') }} as waste_month

from waste_events we


