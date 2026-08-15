with

hires as (

    select
        employee_id,
        hire_date,
        extract(month from hire_date) as hire_month_num,
        extract(year from hire_date) as hire_year,
        department_name,
        location_id
    from {{ ref('dim_employees') }}

),

monthly_hires as (

    select
        hire_month_num,
        hire_year,
        count(*) as hires_count
    from hires
    group by 1, 2

),

avg_by_month as (

    select
        hire_month_num,
        avg(hires_count) as avg_monthly_hires,
        min(hires_count) as min_monthly_hires,
        max(hires_count) as max_monthly_hires,
        count(distinct hire_year) as years_of_data
    from monthly_hires
    group by 1

),

overall_avg as (

    select avg(avg_monthly_hires) as global_avg from avg_by_month

),

final as (

    select
        abm.hire_month_num,
        abm.avg_monthly_hires,
        abm.min_monthly_hires,
        abm.max_monthly_hires,
        abm.years_of_data,
        oa.global_avg,
        abm.avg_monthly_hires / nullif(oa.global_avg, 0) as seasonal_index,
        case
            when abm.avg_monthly_hires > oa.global_avg * 1.3 then 'peak_hiring'
            when abm.avg_monthly_hires < oa.global_avg * 0.7 then 'low_hiring'
            else 'normal_hiring'
        end as hiring_season
    from avg_by_month as abm
    cross join overall_avg as oa

)

select * from final
