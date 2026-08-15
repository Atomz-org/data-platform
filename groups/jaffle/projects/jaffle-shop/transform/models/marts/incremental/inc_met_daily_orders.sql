{{
    config(
        materialized='incremental',
        unique_key='order_metric_key'
    )
}}

with

orders as (

    select * from {{ ref('stg_orders') }}
    {% if is_incremental() %}
    where ordered_at > (select max(order_date) from {{ this }})
    {% endif %}

),

daily_agg as (

    select
        location_id as store_id,
        {{ dbt.date_trunc('day', 'ordered_at') }} as order_date,
        count(*) as total_orders,
        count(distinct customer_id) as unique_customers,
        sum(order_total) as total_order_value,
        round(avg(order_total), 2) as avg_order_value

    from orders
    group by location_id, {{ dbt.date_trunc('day', 'ordered_at') }}

)

select
    store_id || '-' || cast(order_date as varchar) as order_metric_key,
    store_id,
    order_date,
    total_orders,
    unique_customers,
    total_order_value,
    avg_order_value

from daily_agg
