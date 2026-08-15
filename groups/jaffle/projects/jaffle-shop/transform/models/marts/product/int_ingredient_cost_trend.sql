with

ingredient_prices as (

    select * from {{ ref('stg_ingredient_prices') }}

),

monthly_avg as (

    select
        ingredient_id,
        {{ dbt.date_trunc('month', 'effective_from_date') }} as price_month,
        avg(unit_cost) as avg_unit_cost,
        min(unit_cost) as min_unit_cost,
        max(unit_cost) as max_unit_cost,
        count(*) as price_record_count

    from ingredient_prices
    group by ingredient_id, {{ dbt.date_trunc('month', 'effective_from_date') }}

),

with_lag as (

    select
        ingredient_id,
        price_month,
        avg_unit_cost,
        min_unit_cost,
        max_unit_cost,
        price_record_count,
        lag(avg_unit_cost) over (
            partition by ingredient_id
            order by price_month
        ) as prev_month_avg_cost,
        case
            when lag(avg_unit_cost) over (
                partition by ingredient_id
                order by price_month
            ) > 0
            then (avg_unit_cost - lag(avg_unit_cost) over (
                partition by ingredient_id
                order by price_month
            )) / lag(avg_unit_cost) over (
                partition by ingredient_id
                order by price_month
            ) * 100
            else null
        end as mom_cost_change_pct

    from monthly_avg

)

select * from with_lag
