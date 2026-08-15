with

monthly_revenue as (

    select * from {{ ref('met_monthly_revenue_by_store') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

store_revenue as (

    select
        location_id,
        avg(monthly_revenue) as avg_monthly_revenue

    from monthly_revenue
    group by location_id

),

area_stats as (

    select
        left(l.location_name, 1) as area_proxy,
        count(distinct sr.location_id) as stores_in_area,
        sum(sr.avg_monthly_revenue) as area_monthly_revenue,
        avg(sr.avg_monthly_revenue) as area_avg_revenue_per_store

    from store_revenue sr
    left join locations l on sr.location_id = l.location_id
    group by left(l.location_name, 1)

),

optimal as (

    select
        percentile_cont(0.75) within group (order by area_avg_revenue_per_store) as optimal_revenue_per_store

    from area_stats

)

select
    a.area_proxy,
    a.stores_in_area,
    round(a.area_monthly_revenue, 2) as area_monthly_revenue,
    round(a.area_avg_revenue_per_store, 2) as area_avg_revenue_per_store,
    round(o.optimal_revenue_per_store, 2) as optimal_revenue_per_store,
    round(
        (a.area_avg_revenue_per_store * 100.0
        / nullif(o.optimal_revenue_per_store, 0)), 2
    ) as saturation_index,
    case
        when a.area_avg_revenue_per_store >= o.optimal_revenue_per_store then 'undersaturated'
        when a.area_avg_revenue_per_store >= o.optimal_revenue_per_store * 0.7 then 'optimal'
        else 'oversaturated'
    end as saturation_status

from area_stats a
cross join optimal o
