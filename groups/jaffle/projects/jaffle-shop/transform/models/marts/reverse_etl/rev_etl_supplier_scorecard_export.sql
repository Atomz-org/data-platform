with

supplier_scorecard as (

    select * from {{ ref('rpt_supplier_scorecard') }}

)

select
    supplier_id,
    supplier_name,
    fulfillment_rate,
    total_purchase_orders,
    case
        when round(fulfillment_rate * 100, 0) >= 80 then 'preferred'
        when round(fulfillment_rate * 100, 0) >= 60 then 'approved'
        when round(fulfillment_rate * 100, 0) >= 40 then 'conditional'
        else 'under_review'
    end as supplier_status,
    current_timestamp as exported_at

from supplier_scorecard
