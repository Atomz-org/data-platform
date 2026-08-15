with

monthly_maint as (
    select
        {{ sf_date_trunc('month', "completed_date") }} as maint_month,
        location_id,
        count(*) as event_count,
        sum(maintenance_cost) as total_cost
    from {{ ref('fct_maintenance_events') }}
    group by 1, 2
),

compared as (
    select
        maint_month,
        location_id,
        total_cost as current_cost,
        lag(total_cost) over (partition by location_id order by maint_month) as prior_month_cost,
        event_count as current_events,
        lag(event_count) over (partition by location_id order by maint_month) as prior_month_events,
        round(((total_cost - lag(total_cost) over (partition by location_id order by maint_month))) * 100.0
            / nullif(lag(total_cost) over (partition by location_id order by maint_month), 0), 2) as cost_mom_pct
    from monthly_maint
)

select * from compared
