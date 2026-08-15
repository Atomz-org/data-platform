with

qc as (
    select * from {{ ref('stg_po_receipts') }}
),

po as (
    select * from {{ ref('stg_purchase_orders') }}
),

receipt_quality as (
    select
        qc.purchase_order_id,
        po.supplier_id,
        qc.received_at,
        qc.quantity_received,
        qc.quality_status
    from qc
    inner join po on qc.purchase_order_id = po.purchase_order_id
),

final as (
    select
        {{ dbt.date_trunc('month', 'received_at') }} as receipt_month,
        supplier_id,
        count(*) as total_receipts,
        count(case when quality_status = 'rejected' then 1 end) as defects,
        round(count(case when quality_status = 'rejected' then 1 end) * 100.0 / nullif(count(*), 0), 2) as defect_rate_pct
    from receipt_quality
    group by 1, 2
)

select * from final
