with 
r as (
    select * from {{ ref('met_monthly_revenue_by_store') }}
),

w as (
    select * from {{ ref('met_monthly_waste_metrics') }}
),

final as (
    select
        w.month_start,
        w.location_id,
        w.monthly_waste_cost,
        r.monthly_revenue,
        round(w.monthly_waste_cost * 100.0 / nullif(r.monthly_revenue, 0), 2) as waste_to_revenue_pct
    from w
    inner join r
        on w.month_start = r.month_start and w.location_id = r.location_id
)
select * from final
