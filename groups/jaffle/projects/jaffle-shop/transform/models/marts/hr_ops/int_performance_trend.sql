with

reviews as (

    select * from {{ ref('stg_performance_reviews') }}

),

review_with_rolling as (

    select
        review_id,
        employee_id,
        review_date,
        review_period,
        overall_score,
        attendance_score,
        quality_score,
        teamwork_score,
        avg(overall_score) over (
            partition by employee_id
            order by review_date
            rows between 2 preceding and current row
        ) as rolling_avg_score,
        lag(overall_score) over (
            partition by employee_id
            order by review_date
        ) as previous_score,
        row_number() over (
            partition by employee_id
            order by review_date desc
        ) as review_recency_rank

    from reviews

),

final as (

    select
        review_id,
        employee_id,
        review_date,
        review_period,
        overall_score,
        attendance_score,
        quality_score,
        teamwork_score,
        rolling_avg_score,
        previous_score,
        review_recency_rank,
        case
            when previous_score is null then 'initial'
            when overall_score > previous_score then 'improving'
            when overall_score < previous_score then 'declining'
            else 'stable'
        end as trend_direction

    from review_with_rolling

)

select * from final
