with

daily_sales as (

    select * from {{ ref('int_product_sales_daily') }}

),

with_velocity as (

    select
        sale_date,
        product_id,
        product_name,
        product_type,
        units_sold,
        order_count,
        daily_revenue,

        -- 7-day velocity (units per day)
        round(
            (avg(units_sold) over (
                partition by product_id
                order by sale_date
                rows between 6 preceding and current row
            )), 2
        ) as velocity_7d,

        -- 28-day velocity (units per day)
        round(
            (avg(units_sold) over (
                partition by product_id
                order by sale_date
                rows between 27 preceding and current row
            )), 2
        ) as velocity_28d,

        -- 7-day total
        sum(units_sold) over (
            partition by product_id
            order by sale_date
            rows between 6 preceding and current row
        ) as units_last_7d,

        -- 28-day total
        sum(units_sold) over (
            partition by product_id
            order by sale_date
            rows between 27 preceding and current row
        ) as units_last_28d,

        -- Velocity ratio: short-term vs long-term (>1 = accelerating)
        case
            when avg(units_sold) over (
                partition by product_id
                order by sale_date
                rows between 27 preceding and current row
            ) > 0
            then round(
                (avg(units_sold) over (
                    partition by product_id
                    order by sale_date
                    rows between 6 preceding and current row
                ) / avg(units_sold) over (
                    partition by product_id
                    order by sale_date
                    rows between 27 preceding and current row
                )), 4
            )
            else null
        end as velocity_ratio,

        -- Peak detection: is today above 28-day average?
        case
            when units_sold > avg(units_sold) over (
                partition by product_id
                order by sale_date
                rows between 27 preceding and current row
            ) * 1.5
            then true
            else false
        end as is_spike_day

    from daily_sales

)

select * from with_velocity
