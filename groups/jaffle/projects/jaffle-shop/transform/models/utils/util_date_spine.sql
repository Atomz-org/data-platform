with

days as (

    {{ dbt_date.get_base_dates(n_dateparts=3650, datepart="day") }}

),

date_spine as (

    select
        cast(date_day as date) as date_day,
        {{ dbt.date_trunc('week', 'date_day') }} as week_start,
        {{ dbt.date_trunc('month', 'date_day') }} as month_start,
        {{ dbt.date_trunc('quarter', 'date_day') }} as quarter_start,
        extract(year from date_day) as year,
        {{ day_of_week_number('date_day') }} as day_of_week,
        case {{ day_of_week_number('date_day') }}
            when 0 then 'Sunday'
            when 1 then 'Monday'
            when 2 then 'Tuesday'
            when 3 then 'Wednesday'
            when 4 then 'Thursday'
            when 5 then 'Friday'
            when 6 then 'Saturday'
        end as day_name,
        case
            when {{ day_of_week_number('date_day') }} in (0, 6) then true
            else false
        end as is_weekend

    from days

)

select * from date_spine
