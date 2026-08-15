with

receipts as (

    select * from {{ ref('stg_po_receipts') }}

),

quality_summary as (

    select
        purchase_order_id,
        count(receipt_id) as total_receipts,
        sum(quantity_received) as total_quantity_received,
        count(case when quality_status = 'passed' then 1 end) as passed_count,
        count(case when quality_status = 'failed' then 1 end) as failed_count,
        count(case when quality_status = 'partial' then 1 end) as partial_count,
        case
            when count(receipt_id) > 0
                then round(cast(
                    count(case when quality_status = 'passed' then 1 end) * 100.0
                    / count(receipt_id)
                as {{ dbt.type_float() }}), 2)
            else 0
        end as quality_pass_rate_pct,
        min(received_at) as first_receipt_date,
        max(received_at) as last_receipt_date
    from receipts
    group by 1

)

select * from quality_summary
