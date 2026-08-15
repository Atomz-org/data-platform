with

locations as (

    select
        location_id as location_id,
        location_name as store_name,
        opened_date

    from {{ ref('stg_locations') }}

),

monthly_revenue as (

    select * from {{ ref('met_monthly_revenue_by_store') }}

),

store_months as (

    select
        mr.location_id,
        l.store_name,
        l.opened_date,
        mr.month_start,
        mr.monthly_revenue,
        {{ dbt.datediff('l.opened_date', 'mr.month_start', 'month') }} as months_since_opening

    from monthly_revenue mr
    inner join locations l on mr.location_id = l.location_id
    where l.opened_date is not null

)

select
    months_since_opening,
    count(distinct location_id) as store_count,
    round(avg(monthly_revenue), 2) as avg_revenue,
    round(min(monthly_revenue), 2) as min_revenue,
    round(max(monthly_revenue), 2) as max_revenue,
    round(percentile_cont(0.5) within group (order by monthly_revenue), 2) as median_revenue

from store_months
where months_since_opening >= 0
group by months_since_opening
order by months_since_opening
