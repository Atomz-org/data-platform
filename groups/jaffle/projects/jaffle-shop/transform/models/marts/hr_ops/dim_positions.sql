with

positions as (

    select * from {{ ref('stg_positions') }}

),

final as (

    select
        position_id,
        department_id,
        position_title,
        pay_grade,
        min_hourly_rate,
        max_hourly_rate,
        is_management,
        max_hourly_rate - min_hourly_rate as pay_range_spread

    from positions

)

select * from final
