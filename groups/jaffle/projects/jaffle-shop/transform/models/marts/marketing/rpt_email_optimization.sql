with

send_time_analysis as (

    select * from {{ ref('int_email_send_time_analysis') }}

),

-- Rank time slots by engagement
ranked_slots as (

    select
        hour_of_day,
        day_of_week,
        total_sent,
        total_opened,
        total_clicked,
        open_rate,
        click_rate,
        click_to_send_rate,
        -- Day name for readability
        case day_of_week
            when 0 then 'Sunday'
            when 1 then 'Monday'
            when 2 then 'Tuesday'
            when 3 then 'Wednesday'
            when 4 then 'Thursday'
            when 5 then 'Friday'
            when 6 then 'Saturday'
        end as day_name,
        -- Time period bucket
        case
            when hour_of_day between 6 and 9 then 'early_morning'
            when hour_of_day between 10 and 12 then 'late_morning'
            when hour_of_day between 13 and 15 then 'early_afternoon'
            when hour_of_day between 16 and 18 then 'late_afternoon'
            when hour_of_day between 19 and 22 then 'evening'
            else 'night'
        end as time_period,
        -- Rank by open rate (only for slots with meaningful volume)
        row_number() over (
            order by
                case when total_sent >= 10 then open_rate else 0 end desc
        ) as open_rate_rank,
        -- Rank by click rate
        row_number() over (
            order by
                case when total_sent >= 10 then click_to_send_rate else 0 end desc
        ) as click_rate_rank,
        -- Composite engagement score (weighted: 60% open + 40% click)
        case
            when total_sent >= 10
            then (open_rate * 0.6) + (click_to_send_rate * 0.4)
            else 0
        end as engagement_score

    from send_time_analysis

),

-- Add overall ranking by engagement score
final as (

    select
        *,
        row_number() over (order by engagement_score desc) as overall_rank,
        case
            when engagement_score > 0.3 then 'optimal'
            when engagement_score > 0.15 then 'good'
            when engagement_score > 0.05 then 'average'
            else 'poor'
        end as send_time_quality

    from ranked_slots

)

select * from final
