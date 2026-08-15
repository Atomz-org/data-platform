with

deliveries as (
    select supplier_id, actual_transit_days from {{ ref('fct_deliveries') }}
),

per_supplier as (
    select
        supplier_id,
        count(*) as delivery_count,
        round(avg(actual_transit_days), 2) as mean_lead_time,
        round(percentile_cont(0.50) within group (order by actual_transit_days), 2) as median_lead_time,
        round(percentile_cont(0.90) within group (order by actual_transit_days), 2) as p90_lead_time,
        min(actual_transit_days) as min_lead_time,
        max(actual_transit_days) as max_lead_time,
        max(actual_transit_days) - min(actual_transit_days) as lead_time_range
    from deliveries
    group by 1
)

select * from per_supplier
