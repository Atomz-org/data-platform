with

employee_perf as (
    select
        employee_id,
        avg(overall_score) as avg_overall_score,
        count(*) as review_count
    from {{ ref('stg_performance_reviews') }}
    group by 1
),

ranked as (
    select
        employee_id,
        avg_overall_score,
        review_count,
        rank() over (order by avg_overall_score desc) as performance_rank,
        ntile(4) over (order by avg_overall_score desc) as performance_quartile,
        case
            when avg_overall_score >= 4.5 then 'top_performer'
            when avg_overall_score >= 3.5 then 'strong'
            when avg_overall_score >= 2.5 then 'meets_expectations'
            else 'needs_improvement'
        end as performance_band
    from employee_perf
    where review_count >= 1
)

select * from ranked
