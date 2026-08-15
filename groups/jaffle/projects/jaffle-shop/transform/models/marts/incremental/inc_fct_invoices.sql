{{
    config(
        materialized='incremental',
        unique_key='invoice_id'
    )
}}

with

invoices as (

    select * from {{ ref('stg_invoices') }}
    {% if is_incremental() %}
    where issued_date > (select max(issued_date) from {{ this }})
    {% endif %}

)

select
    invoice_id,
    customer_id,
    order_id,
    issued_date,
    due_date,
    total_amount,
    tax_amount,
    invoice_status,
    {{ dbt.date_trunc('month', 'issued_date') }} as invoice_month,
    case
        when invoice_status = 'paid' then 'closed'
        when due_date < current_date and invoice_status != 'paid' then 'overdue'
        else 'open'
    end as invoice_status_derived

from invoices
