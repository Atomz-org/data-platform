with

refunds_enriched as (

    select * from {{ ref('int_refunds_enriched') }}

),

final as (

    select
        refund_id,
        order_id,
        invoice_id,
        location_id,
        refund_reason,
        refund_status,
        refund_amount,
        invoice_total,
        order_total,
        refund_pct_of_invoice,
        requested_date,
        resolved_date,
        order_date,
        days_to_resolution,
        case
            when refund_status = 'approved' then true
            else false
        end as is_approved,
        case
            when refund_amount = invoice_total then true
            else false
        end as is_full_refund

    from refunds_enriched

)

select * from final
