with

store_profile as (

    select * from {{ ref('dim_store_profile') }}

),

early_performance as (

    select
        location_id,
        month_start,
        monthly_revenue,
        monthly_orders,
        row_number() over (partition by location_id order by month_start asc) as month_number
    from {{ ref('met_monthly_revenue_by_store') }}

),

first_6_months as (

    select
        location_id,
        avg(monthly_revenue) as avg_monthly_revenue_first_6m,
        sum(monthly_revenue) as total_revenue_first_6m,
        sum(monthly_orders) as total_orders_first_6m,
        min(monthly_revenue) as min_monthly_revenue,
        max(monthly_revenue) as max_monthly_revenue
    from early_performance
    where month_number <= 6
    group by 1

),

final as (

    select
        sp.store_id,
        sp.store_name,
        sp.months_of_data,
        sp.total_revenue,
        sp.avg_operating_margin_pct,
        f6.avg_monthly_revenue_first_6m,
        f6.total_revenue_first_6m,
        f6.total_orders_first_6m,
        case
            when sp.total_revenue > 0 and sp.months_of_data > 6
                then round(cast(f6.total_revenue_first_6m * 100.0 / sp.total_revenue as {{ dbt.type_float() }}), 2)
            else null
        end as first_6m_pct_of_total_revenue
    from store_profile as sp
    left join first_6_months as f6
        on sp.store_id = f6.location_id

)

select * from final
