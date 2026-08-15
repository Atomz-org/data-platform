with

suppliers as (

    select * from {{ ref('dim_suppliers') }}

),

reliability as (

    select
        supplier_id,
        reliability_score,
        reliability_tier
    from {{ ref('scr_supplier_reliability') }}

),

spend_summary as (

    select
        supplier_id,
        order_month,
        total_spend,
        count_purchase_orders
    from {{ ref('int_supplier_spend_monthly') }}

),

total_spend as (

    select
        supplier_id,
        sum(total_spend) as total_spend,
        sum(count_purchase_orders) as total_pos,
        count(distinct order_month) as active_months,
        avg(total_spend) as avg_total_spend
    from spend_summary
    group by 1

),

final as (

    select
        s.supplier_id,
        s.supplier_name,
        s.is_active,
        r.reliability_score,
        r.reliability_tier,
        coalesce(ts.total_spend, 0) as total_spend,
        coalesce(ts.total_pos, 0) as total_purchase_orders,
        coalesce(ts.active_months, 0) as active_months,
        coalesce(ts.avg_total_spend, 0) as avg_total_spend,
        case
            when r.reliability_tier = 'high' and coalesce(ts.total_spend, 0) > 0 then 'strategic_partner'
            when r.reliability_tier = 'medium' then 'standard_vendor'
            when r.reliability_tier = 'low' then 'at_risk_vendor'
            else 'inactive'
        end as vendor_classification
    from suppliers as s
    left join reliability as r
        on s.supplier_id = r.supplier_id
    left join total_spend as ts
        on s.supplier_id = ts.supplier_id

)

select * from final
