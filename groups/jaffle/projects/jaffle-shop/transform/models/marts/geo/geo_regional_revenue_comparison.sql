with

monthly_revenue as (

    select * from {{ ref('met_monthly_revenue_by_store') }}

),

store_avg as (

    select
        location_id,
        avg(monthly_revenue) as avg_monthly_revenue

    from monthly_revenue
    group by location_id

),

median_revenue as (

    select
        percentile_cont(0.5) within group (order by avg_monthly_revenue) as median_avg_revenue

    from store_avg

),

classified as (

    select
        sa.location_id,
        sa.avg_monthly_revenue,
        m.median_avg_revenue,
        case
            when sa.avg_monthly_revenue >= m.median_avg_revenue then 'top_half'
            else 'bottom_half'
        end as revenue_group

    from store_avg sa
    cross join median_revenue m

)

select
    revenue_group,
    count(*) as store_count,
    round(avg(avg_monthly_revenue), 2) as group_avg_monthly_revenue,
    round(sum(avg_monthly_revenue), 2) as group_total_avg_revenue,
    round(min(avg_monthly_revenue), 2) as group_min_avg_revenue,
    round(max(avg_monthly_revenue), 2) as group_max_avg_revenue,
    round(avg(avg_monthly_revenue) - (select median_avg_revenue from median_revenue), 2) as diff_from_median

from classified
group by revenue_group
