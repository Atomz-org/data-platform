with

supplier_lead as (
    select
        supplier_id,
        avg(actual_transit_days) as avg_lead_time,
        min(actual_transit_days) as min_lead_time,
        max(actual_transit_days) as max_lead_time,
        count(*) as delivery_count
    from {{ ref('fct_deliveries') }}
    group by 1
),

ranked as (
    select
        supplier_id,
        avg_lead_time,
        min_lead_time,
        max_lead_time,
        delivery_count,
        max_lead_time - min_lead_time as lead_time_range,
        rank() over (order by avg_lead_time asc) as lead_time_rank,
        ntile(4) over (order by avg_lead_time asc) as lead_time_quartile
    from supplier_lead
    where delivery_count >= 3
)

select * from ranked
