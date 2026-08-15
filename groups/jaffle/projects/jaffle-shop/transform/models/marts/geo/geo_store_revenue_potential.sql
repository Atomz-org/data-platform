with

store_profile as (

    select * from {{ ref('dim_store_profile') }}

),

store_revenue as (

    select
        location_id,
        avg(monthly_revenue) as current_avg_revenue

    from {{ ref('met_monthly_revenue_by_store') }}
    group by location_id

),

fleet_stats as (

    select
        percentile_cont(0.75) within group (order by current_avg_revenue) as p75_revenue,
        percentile_cont(0.90) within group (order by current_avg_revenue) as p90_revenue,
        avg(current_avg_revenue) as fleet_avg_revenue

    from store_revenue

)

select
    sp.location_id,
    sp.store_name,
    round(sr.current_avg_revenue, 2) as current_avg_revenue,
    round(fs.fleet_avg_revenue, 2) as fleet_avg_revenue,
    round(fs.p75_revenue, 2) as p75_revenue,
    round(fs.p90_revenue, 2) as p90_revenue,
    round(fs.p75_revenue - sr.current_avg_revenue, 2) as gap_to_p75,
    round(fs.p90_revenue - sr.current_avg_revenue, 2) as gap_to_p90,
    case
        when sr.current_avg_revenue >= fs.p90_revenue then 'at_potential'
        when sr.current_avg_revenue >= fs.p75_revenue then 'near_potential'
        when sr.current_avg_revenue >= fs.fleet_avg_revenue then 'moderate_upside'
        else 'significant_upside'
    end as potential_classification

from store_profile sp
left join store_revenue sr on sp.location_id = sr.location_id
cross join fleet_stats fs
