with

reviews as (

    select
        employee_id,
        review_date,
        overall_score,
        reviewer_id,
        {{ dbt.date_trunc('quarter', 'review_date') }} as review_quarter
    from {{ ref('stg_performance_reviews') }}

),

employees as (

    select
        employee_id,
        department_name,
        position_title
    from {{ ref('dim_employees') }}

),

dept_scores as (

    select
        e.department_name,
        r.review_quarter,
        count(*) as review_count,
        avg(r.overall_score) as avg_score,
        min(r.overall_score) as min_score,
        max(r.overall_score) as max_score,
        sum(case when r.overall_score >= 4 then 1 else 0 end) as high_performers,
        sum(case when r.overall_score < 2.5 then 1 else 0 end) as underperformers
    from reviews as r
    inner join employees as e on r.employee_id = e.employee_id
    group by 1, 2

),

final as (

    select
        department_name,
        review_quarter,
        review_count,
        avg_score,
        min_score,
        max_score,
        high_performers,
        underperformers,
        case
            when review_count > 0
            then cast(high_performers as {{ dbt.type_float() }}) / review_count * 100
            else 0
        end as high_performer_pct,
        lag(avg_score) over (partition by department_name order by review_quarter) as prev_quarter_avg,
        avg_score - coalesce(
            lag(avg_score) over (partition by department_name order by review_quarter),
            avg_score
        ) as score_trend
    from dept_scores

)

select * from final
