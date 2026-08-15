with

weekly_inventory as (
    select
        week_start,
        location_id,
        total_units_on_hand,
        weekly_movements
    from {{ ref('met_weekly_inventory_metrics') }}
),

trended as (
    select
        week_start,
        location_id,
        total_units_on_hand,
        weekly_movements,
        round(weekly_movements * 1.0 / nullif(total_units_on_hand, 0), 2) as turnover_ratio,
        avg(round(weekly_movements * 1.0 / nullif(total_units_on_hand, 0), 2)) over (
            partition by location_id order by week_start
            rows between 3 preceding and current row
        ) as turnover_4w_ma,
        lag(round(weekly_movements * 1.0 / nullif(total_units_on_hand, 0), 2)) over (
            partition by location_id order by week_start
        ) as prev_week_turnover,
        case
            when round(weekly_movements * 1.0 / nullif(total_units_on_hand, 0), 2) >
                avg(round(weekly_movements * 1.0 / nullif(total_units_on_hand, 0), 2)) over (
                    partition by location_id order by week_start
                    rows between 3 preceding and current row
                ) * 1.2 then 'improving'
            when round(weekly_movements * 1.0 / nullif(total_units_on_hand, 0), 2) <
                avg(round(weekly_movements * 1.0 / nullif(total_units_on_hand, 0), 2)) over (
                    partition by location_id order by week_start
                    rows between 3 preceding and current row
                ) * 0.8 then 'declining'
            else 'stable'
        end as turnover_trend
    from weekly_inventory
)

select * from trended
