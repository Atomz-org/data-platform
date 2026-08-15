with

concentration as (

    select * from {{ ref('int_supplier_concentration') }}

),

suppliers as (

    select * from {{ ref('dim_suppliers') }}

),

risk_assessment as (

    select
        concentration.supplier_id,
        concentration.supplier_name,
        suppliers.is_active,
        suppliers.total_contracts,
        suppliers.active_contracts,
        concentration.lifetime_spend,
        concentration.avg_spend_share_pct,
        concentration.max_spend_share_pct,
        concentration.active_months,
        case
            when concentration.avg_spend_share_pct > 0.30
                then 'high_concentration_risk'
            when concentration.avg_spend_share_pct > 0.20
                then 'moderate_concentration_risk'
            when concentration.avg_spend_share_pct > 0.10
                then 'low_concentration_risk'
            else 'diversified'
        end as concentration_risk_level,
        concentration.avg_spend_share_pct > 0.30 as is_concentration_risk

    from concentration

    left join suppliers
        on concentration.supplier_id = suppliers.supplier_id

)

select * from risk_assessment
