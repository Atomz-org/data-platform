with

suppliers as (

    select * from {{ ref('dim_suppliers') }}

),

supplier_spend as (

    select * from {{ ref('int_supplier_spend_monthly') }}

),

supplier_quality as (

    select * from {{ ref('int_supplier_quality_score') }}

),

lead_time as (

    select * from {{ ref('int_lead_time_by_supplier') }}

),

scorecard as (

    select * from {{ ref('rpt_supplier_scorecard') }}

)

select
    s.supplier_id,
    s.supplier_name,
    s.contact_email,
    ss.total_spend,
    ss.count_purchase_orders as total_orders,
    sq.quality_score,
    lt.avg_lead_time_days,
    sc.fulfillment_rate,
    1 - sc.fulfillment_rate as defect_rate,
    case
        when sq.quality_score >= 80 then 'preferred'
        when sq.quality_score >= 60 then 'approved'
        else 'under_review'
    end as supplier_tier

from suppliers s
left join (
    select supplier_id, sum(total_spend) as total_spend, sum(count_purchase_orders) as count_purchase_orders
    from supplier_spend group by supplier_id
) ss on s.supplier_id = ss.supplier_id
left join supplier_quality sq on s.supplier_id = sq.supplier_id
left join lead_time lt on s.supplier_id = lt.supplier_id
left join scorecard sc on s.supplier_id = sc.supplier_id
