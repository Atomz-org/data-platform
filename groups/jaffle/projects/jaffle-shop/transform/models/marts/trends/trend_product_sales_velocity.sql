with

daily_product as (
    select
        sale_date,
        product_id,
        units_sold,
        daily_revenue
    from {{ ref('fct_product_sales') }}
),

trended as (
    select
        sale_date,
        product_id,
        units_sold,
        daily_revenue,
        avg(units_sold) over (
            partition by product_id order by sale_date
            rows between 6 preceding and current row
        ) as qty_7d_ma,
        avg(units_sold) over (
            partition by product_id order by sale_date
            rows between 27 preceding and current row
        ) as qty_28d_ma,
        case
            when avg(units_sold) over (
                partition by product_id order by sale_date
                rows between 6 preceding and current row
            ) > avg(units_sold) over (
                partition by product_id order by sale_date
                rows between 27 preceding and current row
            ) * 1.2 then 'accelerating'
            when avg(units_sold) over (
                partition by product_id order by sale_date
                rows between 6 preceding and current row
            ) < avg(units_sold) over (
                partition by product_id order by sale_date
                rows between 27 preceding and current row
            ) * 0.8 then 'decelerating'
            else 'steady'
        end as velocity_trend
    from daily_product
)

select * from trended
