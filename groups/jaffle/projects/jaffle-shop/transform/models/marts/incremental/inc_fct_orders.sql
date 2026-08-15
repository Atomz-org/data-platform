{{
    config(
        materialized='incremental',
        unique_key='order_id'
    )
}}

with

source_orders as (

    select * from {{ ref('stg_orders') }}
    {% if is_incremental() %}
    where ordered_at > (select max(ordered_at) from {{ this }})
    {% endif %}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

)

select
    o.order_id,
    o.customer_id,
    c.customer_name,
    o.location_id,
    l.location_name,
    o.ordered_at,
    o.order_total,
    o.tax_paid,
    o.order_total - o.tax_paid as subtotal,
    {{ dbt.date_trunc('day', 'o.ordered_at') }} as order_date,
    {{ dbt.date_trunc('month', 'o.ordered_at') }} as order_month,
    extract(hour from o.ordered_at) as order_hour,
    {{ day_of_week_number('o.ordered_at') }} as order_day_of_week

from source_orders o
left join customers c on o.customer_id = c.customer_id
left join locations l on o.location_id = l.location_id
