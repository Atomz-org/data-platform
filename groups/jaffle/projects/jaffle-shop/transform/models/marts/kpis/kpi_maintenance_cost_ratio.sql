with 
r as (
    select * from {{ ref('met_monthly_revenue_by_store') }}
),

monthly_maint as (
    select
        {{ sf_date_trunc('month', "scheduled_date") }} as maint_month,
        location_id,
        sum(maintenance_cost) as total_maintenance_cost
    from {{ ref('fct_maintenance_events') }}
    group by 1, 2
),
final as (
    select
        mm.maint_month,
        mm.location_id,
        mm.total_maintenance_cost,
        r.monthly_revenue,
        round(mm.total_maintenance_cost * 100.0 / nullif(r.monthly_revenue, 0), 2) as maintenance_cost_ratio
    from monthly_maint as mm
    inner join r
        on mm.maint_month = r.month_start and mm.location_id = r.location_id
)
select * from final
