with

shift_coverage as (

    select * from {{ ref('int_shift_coverage') }}

),

labor_demand as (

    select * from {{ ref('int_store_labor_demand') }}

),

coverage_vs_demand as (

    select
        shift_coverage.location_id,
        shift_coverage.location_name,
        shift_coverage.shift_date,
        {{ day_of_week_number('shift_coverage.shift_date') }} as day_of_week,
        shift_coverage.scheduled_staff_count,
        shift_coverage.total_scheduled_hours,
        coalesce(labor_demand.predicted_labor_hours_needed, 0) as predicted_hours_needed,
        coalesce(labor_demand.avg_daily_orders, 0) as avg_expected_orders,
        case
            when coalesce(labor_demand.predicted_labor_hours_needed, 0) > 0
                then round(
                    (shift_coverage.total_scheduled_hours
                    - labor_demand.predicted_labor_hours_needed), 1
                )
            else null
        end as hours_surplus_deficit,
        case
            when coalesce(labor_demand.predicted_labor_hours_needed, 0) > 0
                then round(
                    (shift_coverage.total_scheduled_hours * 100.0
                    / labor_demand.predicted_labor_hours_needed), 1
                )
            else null
        end as coverage_pct

    from shift_coverage
    left join labor_demand
        on shift_coverage.location_id = labor_demand.location_id
        and {{ day_of_week_number('shift_coverage.shift_date') }} = labor_demand.day_of_week

),

gap_analysis as (

    select
        location_id,
        location_name,
        shift_date,
        day_of_week,
        scheduled_staff_count,
        total_scheduled_hours,
        predicted_hours_needed,
        avg_expected_orders,
        hours_surplus_deficit,
        coverage_pct,
        case
            when coverage_pct < 80 then 'critically_understaffed'
            when coverage_pct < 95 then 'understaffed'
            when coverage_pct > 120 then 'overstaffed'
            else 'adequately_staffed'
        end as staffing_assessment,
        case
            when coverage_pct < 80 then 3
            when coverage_pct < 95 then 2
            when coverage_pct > 120 then 1
            else 0
        end as gap_severity

    from coverage_vs_demand

),

chronic_gaps as (

    select
        location_id,
        location_name,
        day_of_week,
        count(*) as total_occurrences,
        sum(case when staffing_assessment in ('critically_understaffed', 'understaffed') then 1 else 0 end) as understaffed_occurrences,
        round(avg(coverage_pct), 1) as avg_coverage_pct,
        round(avg(hours_surplus_deficit), 1) as avg_hours_gap,
        case
            when sum(case when staffing_assessment in ('critically_understaffed', 'understaffed') then 1 else 0 end) * 100.0
                / count(*) > 50
                then true
            else false
        end as is_chronic_gap

    from gap_analysis
    group by
        location_id,
        location_name,
        day_of_week

)

select * from chronic_gaps
