with

locations as (

    select * from {{ ref('stg_locations') }}

),

monthly_revenue as (

    select * from {{ ref('met_monthly_revenue_by_store') }}

),

store_region as (

    select
        location_id as store_id,
        location_name as store_name,
        -- Use first character of store location_name or id range as region proxy
        left(location_name, 1) as region_proxy

    from locations

),

region_stats as (

    select
        sr.region_proxy,
        count(distinct sr.store_id) as store_count,
        avg(mr.monthly_revenue) as avg_store_monthly_revenue,
        sum(mr.monthly_revenue) as total_region_revenue

    from store_region sr
    left join monthly_revenue mr on sr.store_id = mr.location_id
    group by sr.region_proxy

)

select
    region_proxy,
    store_count,
    round(avg_store_monthly_revenue, 2) as avg_store_monthly_revenue,
    round(total_region_revenue, 2) as total_region_revenue,
    round(total_region_revenue / nullif(store_count, 0), 2) as revenue_per_store

from region_stats
