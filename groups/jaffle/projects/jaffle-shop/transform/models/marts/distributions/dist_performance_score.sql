with

reviews as (
    select employee_id, overall_score from {{ ref('stg_performance_reviews') }}
),

stats as (
    select
        round(avg(overall_score), 2) as mean_overall_score,
        round(percentile_cont(0.25) within group (order by overall_score), 2) as p25_overall_score,
        round(percentile_cont(0.50) within group (order by overall_score), 2) as median_overall_score,
        round(percentile_cont(0.75) within group (order by overall_score), 2) as p75_overall_score
    from reviews
),

bucketed as (
    select
        case
            when overall_score >= 4.5 then 'exceptional'
            when overall_score >= 3.5 then 'above_average'
            when overall_score >= 2.5 then 'meets_expectations'
            when overall_score >= 1.5 then 'needs_improvement'
            else 'unsatisfactory'
        end as overall_score_bucket,
        count(*) as review_count,
        round(avg(overall_score), 2) as avg_in_bucket
    from reviews
    group by 1
)

select b.*, s.mean_overall_score, s.median_overall_score
from bucketed as b cross join stats as s
