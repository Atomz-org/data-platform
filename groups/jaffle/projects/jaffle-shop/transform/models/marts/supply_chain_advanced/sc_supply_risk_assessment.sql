with

diversification as (

    select
        product_id,
        active_suppliers,
        supply_risk_level as source_risk
    from {{ ref('sc_supplier_diversification') }}

),

volatility as (

    select
        ingredient_id as product_id,
        volatility_category
    from {{ ref('sc_ingredient_price_volatility') }}

),

lead_times as (

    select
        supplier_id,
        avg_lead_time_days,
        case
            when avg_lead_time_days > 14 then 'long'
            when avg_lead_time_days > 7 then 'medium'
            else 'short'
        end as lead_time_risk
    from {{ ref('int_lead_time_by_supplier') }}

),

avg_lead_risk as (

    select
        case
            when avg(avg_lead_time_days) > 14 then 'long'
            when avg(avg_lead_time_days) > 7 then 'medium'
            else 'short'
        end as overall_lead_time_risk
    from lead_times

),

final as (

    select
        d.product_id,
        d.active_suppliers,
        d.source_risk,
        coalesce(v.volatility_category, 'unknown') as price_volatility,
        alr.overall_lead_time_risk as lead_time_risk,
        -- Composite risk score: 0-3
        (case when d.source_risk = 'high' then 1 else 0 end)
        + (case when v.volatility_category = 'high_volatility' then 1 else 0 end)
        + (case when alr.overall_lead_time_risk = 'long' then 1 else 0 end)
        as composite_risk_score,
        case
            when (case when d.source_risk = 'high' then 1 else 0 end)
                + (case when v.volatility_category = 'high_volatility' then 1 else 0 end)
                + (case when alr.overall_lead_time_risk = 'long' then 1 else 0 end) >= 2
            then 'critical_risk'
            when (case when d.source_risk = 'high' then 1 else 0 end)
                + (case when v.volatility_category = 'high_volatility' then 1 else 0 end)
                + (case when alr.overall_lead_time_risk = 'long' then 1 else 0 end) = 1
            then 'elevated_risk'
            else 'acceptable_risk'
        end as overall_risk_level
    from diversification as d
    left join volatility as v on d.product_id = v.product_id
    cross join avg_lead_risk as alr

)

select * from final
