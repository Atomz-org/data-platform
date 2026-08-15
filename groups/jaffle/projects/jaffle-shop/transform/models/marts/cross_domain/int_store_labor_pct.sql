with monthly_labor as (
    select
        location_id as location_id,
        {{ dbt.date_trunc("month", "work_date") }} as labor_month,
        sum(total_labor_cost) as monthly_labor_cost
    from {{ ref('int_labor_cost_daily') }}
    group by location_id, {{ dbt.date_trunc("month", "work_date") }}
),

monthly_revenue as (
    select
        location_id as location_id,
        {{ dbt.date_trunc("month", "revenue_date") }} as month_start,
        sum(total_revenue) as monthly_revenue
    from {{ ref('int_revenue_by_store_daily') }}
    group by location_id, {{ dbt.date_trunc("month", "revenue_date") }}
),

fleet_avg as (
    select
        r.month_start,
        sum(l.monthly_labor_cost) / nullif(sum(r.monthly_revenue), 0) * 100 as fleet_labor_pct
    from monthly_revenue as r
    inner join monthly_labor as l
        on r.location_id = l.location_id
        and r.month_start = l.labor_month
    group by r.month_start
)

select
    r.location_id,
    r.month_start as month_start,
    r.monthly_revenue,
    coalesce(l.monthly_labor_cost, 0) as monthly_labor_cost,
    case
        when r.monthly_revenue > 0
            then round(
                (cast(coalesce(l.monthly_labor_cost, 0) as {{ dbt.type_float() }})
                / r.monthly_revenue * 100), 2
            )
        else 0
    end as labor_cost_pct,
    round(cast(fa.fleet_labor_pct as {{ dbt.type_float() }}), 2) as fleet_avg_labor_pct,
    case
        when r.monthly_revenue > 0
            then round(
                (cast(coalesce(l.monthly_labor_cost, 0) as {{ dbt.type_float() }})
                / r.monthly_revenue * 100 - fa.fleet_labor_pct), 2
            )
        else 0
    end as labor_pct_vs_fleet
from monthly_revenue as r
left join monthly_labor as l
    on r.location_id = l.location_id
    and r.month_start = l.labor_month
left join fleet_avg as fa
    on r.month_start = fa.month_start
