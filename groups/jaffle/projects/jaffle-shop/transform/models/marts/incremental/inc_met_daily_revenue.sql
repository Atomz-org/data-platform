{{
    config(
        materialized='incremental',
        unique_key='revenue_key'
    )
}}

with

invoices as (

    select * from {{ ref('stg_invoices') }}
    {% if is_incremental() %}
    where issued_date > (select max(revenue_date) from {{ this }})
    {% endif %}

),

daily_agg as (

    select
        customer_id,
        {{ dbt.date_trunc('day', 'issued_date') }} as revenue_date,
        sum(total_amount) as daily_revenue,
        sum(tax_amount) as daily_tax,
        count(*) as invoice_count

    from invoices
    group by customer_id, {{ dbt.date_trunc('day', 'issued_date') }}

)

select
    customer_id || '-' || cast(revenue_date as varchar) as revenue_key,
    customer_id,
    revenue_date,
    daily_revenue,
    daily_tax,
    invoice_count

from daily_agg
