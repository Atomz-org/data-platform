with

supplier_metrics as (
    select
        supplier_id,
        count(*) as total_deliveries,
        count(case when is_on_time then 1 end) as on_time_deliveries,
        round(count(case when is_on_time then 1 end) * 100.0 / nullif(count(*), 0), 2) as on_time_pct,
        avg(actual_transit_days) as avg_lead_time
    from {{ ref('fct_deliveries') }}
    group by 1
),

ranked as (
    select
        supplier_id,
        total_deliveries,
        on_time_pct,
        avg_lead_time,
        rank() over (order by on_time_pct desc) as reliability_rank,
        ntile(4) over (order by on_time_pct desc) as reliability_quartile
    from supplier_metrics
    where total_deliveries >= 3
)

select * from ranked
