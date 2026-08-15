with

locations as (

    select
        location_id as store_id,
        location_name as store_name,
        opened_date

    from {{ ref('stg_locations') }}

),

monthly_revenue as (

    select * from {{ ref('met_monthly_revenue_by_store') }}

),

new_stores as (

    select
        store_id as new_store_id,
        store_name as new_store_name,
        opened_date as new_store_opened_date,
        {{ dbt.date_trunc('month', 'opened_date') }} as opening_month

    from locations
    where opened_date is not null

),

existing_store_revenue as (

    select
        mr.location_id as existing_store_id,
        ns.new_store_id,
        ns.new_store_name,
        ns.opening_month,
        avg(case
            when mr.month_start >= ns.opening_month - interval '3 months'
                and mr.month_start < ns.opening_month
            then mr.monthly_revenue
        end) as avg_revenue_before,
        avg(case
            when mr.month_start >= ns.opening_month
                and mr.month_start < ns.opening_month + interval '3 months'
            then mr.monthly_revenue
        end) as avg_revenue_after

    from monthly_revenue mr
    cross join new_stores ns
    where mr.location_id != ns.new_store_id
    group by mr.location_id, ns.new_store_id, ns.new_store_name, ns.opening_month

)

select
    existing_store_id,
    new_store_id,
    new_store_name,
    opening_month,
    round(avg_revenue_before, 2) as avg_revenue_3m_before,
    round(avg_revenue_after, 2) as avg_revenue_3m_after,
    round(avg_revenue_after - avg_revenue_before, 2) as revenue_change,
    round(
        (avg_revenue_after - avg_revenue_before) * 100.0
        / nullif(avg_revenue_before, 0), 2
    ) as pct_revenue_change,
    case
        when (avg_revenue_after - avg_revenue_before) * 100.0
            / nullif(avg_revenue_before, 0) < -10
        then 'significant_negative_impact'
        when (avg_revenue_after - avg_revenue_before) * 100.0
            / nullif(avg_revenue_before, 0) < -5
        then 'moderate_negative_impact'
        else 'minimal_impact'
    end as impact_classification

from existing_store_revenue
where avg_revenue_before is not null and avg_revenue_after is not null
