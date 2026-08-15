with

employees_by_store as (

    select
        location_id,
        count(distinct employee_id) as employee_count
    from {{ ref('dim_employees') }}
    where employment_status = 'active'
    group by 1

),

monthly_revenue as (

    select
        location_id,
        month_start,
        monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}

),

locations as (

    select
        location_id,
        location_name
    from {{ ref('stg_locations') }}

),

final as (

    select
        mr.location_id,
        l.location_name,
        mr.month_start,
        mr.monthly_revenue,
        coalesce(ebs.employee_count, 0) as staff_count,
        case
            when coalesce(ebs.employee_count, 0) > 0
                then round(cast(mr.monthly_revenue / ebs.employee_count as {{ dbt.type_float() }}), 2)
            else null
        end as revenue_per_employee,
        case
            when mr.monthly_revenue > 0 and coalesce(ebs.employee_count, 0) > 0
                then round(cast(ebs.employee_count * 10000.0 / mr.monthly_revenue as {{ dbt.type_float() }}), 2)
            else null
        end as staff_per_10k_revenue
    from monthly_revenue as mr
    left join employees_by_store as ebs
        on mr.location_id = ebs.location_id
    left join locations as l
        on mr.location_id = l.location_id

)

select * from final
