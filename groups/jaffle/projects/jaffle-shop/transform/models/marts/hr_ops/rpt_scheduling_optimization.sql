with

shift_coverage as (

    select * from {{ ref('int_shift_coverage') }}

),

staffing_ratio as (

    select * from {{ ref('int_store_staffing_ratio') }}

),

daily_metrics as (

    select
        staffing_ratio.location_id,
        staffing_ratio.location_name,
        staffing_ratio.shift_date,
        staffing_ratio.scheduled_staff_count,
        staffing_ratio.total_scheduled_hours,
        staffing_ratio.order_count,
        staffing_ratio.staff_hours_per_order,
        staffing_ratio.orders_per_staff

    from staffing_ratio

),

weekly_summary as (

    select
        location_id,
        location_name,
        {{ dbt.date_trunc('week', 'shift_date') }} as report_week,
        avg(scheduled_staff_count) as avg_daily_staff,
        sum(total_scheduled_hours) as total_weekly_scheduled_hours,
        sum(order_count) as total_weekly_orders,
        avg(staff_hours_per_order) as avg_staff_hours_per_order,
        avg(orders_per_staff) as avg_orders_per_staff,
        min(scheduled_staff_count) as min_daily_staff,
        max(scheduled_staff_count) as max_daily_staff,
        -- NOTE: staffing thresholds based on 2024 benchmark data
        case
            when avg(orders_per_staff) > 20 then 'understaffed'
            when avg(orders_per_staff) < 5 then 'overstaffed'
            else 'balanced'
        end as staffing_assessment

    from daily_metrics
    where extract(year from shift_date) = 2024
    group by
        location_id,
        location_name,
        {{ dbt.date_trunc('week', 'shift_date') }}

)

select * from weekly_summary
