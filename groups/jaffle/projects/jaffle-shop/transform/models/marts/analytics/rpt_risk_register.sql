with

supplier_risk as (

    select
        supplier_id,
        supplier_name,
        reliability_score,
        reliability_tier,
        'supplier_reliability' as risk_domain,
        case when reliability_tier = 'low' then 'high' when reliability_tier = 'medium' then 'medium' else 'low' end as risk_level
    from {{ ref('scr_supplier_reliability') }}
    where reliability_tier in ('low', 'medium')

),

store_risk as (

    select
        location_id,
        store_name,
        store_health_score,
        health_tier,
        'store_health' as risk_domain,
        case when health_tier = 'critical' then 'high' when health_tier = 'at_risk' then 'medium' else 'low' end as risk_level
    from {{ ref('scr_store_health') }}
    where health_tier in ('critical', 'at_risk')

),

churn_risk as (

    select
        customer_id,
        customer_name,
        churn_propensity_score,
        churn_risk_tier,
        'customer_churn' as risk_domain,
        churn_risk_tier as risk_level
    from {{ ref('scr_customer_churn_propensity') }}
    where churn_risk_tier = 'high'

),

risk_summary as (

    select
        'supplier_reliability' as risk_domain,
        count(*) as risk_count,
        'Suppliers with low or medium reliability scores' as risk_description
    from supplier_risk

    union all

    select
        'store_health' as risk_domain,
        count(*) as risk_count,
        'Stores with critical or at-risk health scores' as risk_description
    from store_risk

    union all

    select
        'customer_churn' as risk_domain,
        count(*) as risk_count,
        'Customers with high churn risk' as risk_description
    from churn_risk

)

select * from risk_summary
