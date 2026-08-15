with

productivity as (

    select
        employee_id,
        avg(orders_per_hour) as avg_orders_per_hour,
        sum(total_hours_worked) as total_hours_worked,
        count(work_date) as days_worked
    from {{ ref('int_employee_productivity') }}
    group by employee_id

),

absenteeism as (

    select * from {{ ref('int_absenteeism_rate') }}

),

training as (

    select * from {{ ref('int_training_progress') }}

),

reviews as (

    select
        employee_id,
        overall_score as latest_review_score,
        rolling_avg_score,
        trend_direction
    from {{ ref('int_performance_trend') }}
    where review_recency_rank = 1

),

scored as (

    select
        p.employee_id,
        p.avg_orders_per_hour,
        p.total_hours_worked,
        p.days_worked,

        -- Productivity component (0-30)
        case
            when p.avg_orders_per_hour >= 10 then 30
            when p.avg_orders_per_hour >= 7 then 24
            when p.avg_orders_per_hour >= 5 then 18
            when p.avg_orders_per_hour >= 3 then 10
            else 5
        end as productivity_score,

        -- Attendance component (0-25): lower absenteeism = better
        case
            when coalesce(a.absenteeism_rate_pct, 100) <= 2 then 25
            when coalesce(a.absenteeism_rate_pct, 100) <= 5 then 20
            when coalesce(a.absenteeism_rate_pct, 100) <= 10 then 12
            when coalesce(a.absenteeism_rate_pct, 100) <= 20 then 5
            else 0
        end as attendance_score,

        -- Training completion component (0-20)
        case
            when coalesce(t.required_completion_pct, 0) >= 100 then 20
            when coalesce(t.required_completion_pct, 0) >= 80 then 16
            when coalesce(t.required_completion_pct, 0) >= 50 then 10
            when coalesce(t.required_completion_pct, 0) >= 25 then 5
            else 0
        end as training_score,

        -- Review score component (0-25)
        case
            when coalesce(r.latest_review_score, 0) >= 4.5 then 25
            when coalesce(r.latest_review_score, 0) >= 4.0 then 20
            when coalesce(r.latest_review_score, 0) >= 3.5 then 15
            when coalesce(r.latest_review_score, 0) >= 3.0 then 8
            else 0
        end as review_score_component,

        -- Raw metrics
        coalesce(a.absenteeism_rate_pct, 0) as absenteeism_rate_pct,
        coalesce(t.required_completion_pct, 0) as training_completion_pct,
        coalesce(r.latest_review_score, 0) as latest_review_score,
        coalesce(r.trend_direction, 'unknown') as review_trend_direction

    from productivity as p

    left join absenteeism as a
        on p.employee_id = a.employee_id

    left join training as t
        on p.employee_id = t.employee_id

    left join reviews as r
        on p.employee_id = r.employee_id

),

final as (

    select
        *,
        productivity_score + attendance_score + training_score + review_score_component as performance_score,
        case
            when productivity_score + attendance_score + training_score + review_score_component >= 80 then 'top_performer'
            when productivity_score + attendance_score + training_score + review_score_component >= 60 then 'solid'
            when productivity_score + attendance_score + training_score + review_score_component >= 40 then 'developing'
            else 'needs_support'
        end as performance_tier

    from scored

)

select * from final
