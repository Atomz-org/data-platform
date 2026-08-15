with

store_profile as (
    select * from {{ ref('dim_store_profile') }}
),

store_revenue as (
    select
        location_id,
        count(distinct month_start) as months_of_data,
        sum(monthly_revenue) as total_revenue,
        avg(monthly_revenue) as avg_monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}
    group by location_id
),

final as (
    select
        sp.location_id,
        sp.store_name,
        coalesce(sr.months_of_data, 0) as months_of_data,
        coalesce(sr.total_revenue, 0) as total_revenue,
        coalesce(sr.avg_monthly_revenue, 0) as avg_monthly_revenue,
        rank() over (order by coalesce(sr.avg_monthly_revenue, 0) desc) as revenue_rank
    from store_profile as sp
    left join store_revenue as sr on sp.location_id = sr.location_id
)

select * from final
