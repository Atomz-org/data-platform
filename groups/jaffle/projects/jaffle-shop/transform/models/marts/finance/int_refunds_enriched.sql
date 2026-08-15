with

refunds as (

    select * from {{ ref('stg_refunds') }}

),

invoices as (

    select * from {{ ref('stg_invoices') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

enriched as (

    select
        r.refund_id,
        r.order_id,
        r.invoice_id,
        r.refund_reason,
        r.refund_status,
        r.refund_amount,
        r.requested_date,
        r.resolved_date,
        inv.total_amount as invoice_total,
        inv.invoice_status,
        o.order_total,
        o.location_id,
        o.ordered_at as order_date,
        case
            when inv.total_amount > 0
                then r.refund_amount / inv.total_amount
            else 0
        end as refund_pct_of_invoice,
        case
            when r.resolved_date is not null
                then {{ sf_datediff('day', "r.requested_date", "r.resolved_date") }}
        end as days_to_resolution

    from refunds as r
    left join invoices as inv
        on r.invoice_id = inv.invoice_id
    left join orders as o
        on r.order_id = o.order_id

)

select * from enriched
