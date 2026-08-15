with

qc as (
    select * from {{ ref('int_receipt_quality_check') }}
),

po as (
    select * from {{ ref('stg_purchase_orders') }}
),

quality_check as (
    select
        qc.last_receipt_date,
        po.supplier_id,
        qc.purchase_order_id,
        qc.quality_pass_rate_pct,
        'quality_check_failure' as rejection_reason
    from qc
    inner join po on qc.purchase_order_id = po.purchase_order_id
    where qc.quality_pass_rate_pct < 100
),

alerts as (
    select
        last_receipt_date,
        supplier_id,
        purchase_order_id,
        quality_pass_rate_pct,
        rejection_reason,
        'supplier_quality_issue' as alert_type,
        'warning' as severity
    from quality_check
)

select * from alerts
