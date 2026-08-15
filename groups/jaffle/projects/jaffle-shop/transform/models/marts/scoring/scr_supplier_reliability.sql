with

suppliers as (

    select * from {{ ref('dim_suppliers') }}

),

quality as (

    select * from {{ ref('int_supplier_quality_score') }}

),

lead_time as (

    select * from {{ ref('int_lead_time_by_supplier') }}

),

on_time as (

    select * from {{ ref('int_delivery_on_time_rate') }}

),

scored as (

    select
        s.supplier_id,
        s.supplier_name,
        s.is_active,
        s.active_contracts,

        -- On-time delivery component (0-30)
        case
            when coalesce(ot.on_time_rate, 0) >= 0.95 then 30
            when coalesce(ot.on_time_rate, 0) >= 0.90 then 24
            when coalesce(ot.on_time_rate, 0) >= 0.80 then 18
            when coalesce(ot.on_time_rate, 0) >= 0.70 then 10
            else 5
        end as delivery_score,

        -- Quality component (0-30)
        case
            when coalesce(q.quality_score, 0) >= 0.98 then 30
            when coalesce(q.quality_score, 0) >= 0.95 then 24
            when coalesce(q.quality_score, 0) >= 0.90 then 18
            when coalesce(q.quality_score, 0) >= 0.80 then 10
            else 5
        end as quality_component_score,

        -- Price stability / waste cost component (0-20): lower waste = better
        case
            when coalesce(q.total_waste_cost, 0) = 0 then 20
            when coalesce(q.total_waste_cost, 0) < 100 then 15
            when coalesce(q.total_waste_cost, 0) < 500 then 10
            when coalesce(q.total_waste_cost, 0) < 1000 then 5
            else 0
        end as price_stability_score,

        -- Lead time consistency component (0-20): smaller variance = better
        case
            when coalesce(lt.avg_lead_time_variance_days, 0) <= 0 then 20
            when coalesce(lt.avg_lead_time_variance_days, 0) <= 1 then 16
            when coalesce(lt.avg_lead_time_variance_days, 0) <= 3 then 10
            when coalesce(lt.avg_lead_time_variance_days, 0) <= 7 then 5
            else 0
        end as lead_time_consistency_score,

        -- Raw metrics for reference
        coalesce(ot.on_time_rate, 0) as on_time_rate,
        coalesce(q.quality_score, 0) as quality_score,
        coalesce(q.defect_rate, 0) as defect_rate,
        coalesce(lt.avg_lead_time_days, 0) as avg_lead_time_days,
        coalesce(lt.avg_lead_time_variance_days, 0) as avg_lead_time_variance_days

    from suppliers as s

    left join quality as q
        on s.supplier_id = q.supplier_id

    left join lead_time as lt
        on s.supplier_id = lt.supplier_id

    left join on_time as ot
        on s.supplier_id = ot.supplier_id

),

final as (

    select
        *,
        delivery_score + quality_component_score + price_stability_score + lead_time_consistency_score as reliability_score,
        case
            when delivery_score + quality_component_score + price_stability_score + lead_time_consistency_score >= 80 then 'excellent'
            when delivery_score + quality_component_score + price_stability_score + lead_time_consistency_score >= 60 then 'good'
            when delivery_score + quality_component_score + price_stability_score + lead_time_consistency_score >= 40 then 'fair'
            else 'poor'
        end as reliability_tier

    from scored

)

select * from final
