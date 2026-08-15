with

date_spine as (

    select * from {{ ref('util_date_spine') }}

),

-- Fiscal year starts February 1
fiscal_mapping as (

    select
        date_day,
        week_start,
        month_start,
        quarter_start,
        year,
        day_of_week,
        day_name,
        is_weekend,

        -- Fiscal year: if month >= Feb, fiscal year = calendar year
        -- if month = Jan, fiscal year = calendar year - 1
        case
            when extract(month from date_day) >= 2
                then extract(year from date_day)
            else extract(year from date_day) - 1
        end as fiscal_year,

        -- Fiscal month: Feb=1, Mar=2, ..., Jan=12
        case
            when extract(month from date_day) >= 2
                then extract(month from date_day) - 1
            else 12
        end as fiscal_month,

        -- Fiscal quarter: FM 1-3 = FQ1, FM 4-6 = FQ2, FM 7-9 = FQ3, FM 10-12 = FQ4
        case
            when extract(month from date_day) between 2 and 4 then 1
            when extract(month from date_day) between 5 and 7 then 2
            when extract(month from date_day) between 8 and 10 then 3
            else 4
        end as fiscal_quarter

    from date_spine

)

select * from fiscal_mapping
