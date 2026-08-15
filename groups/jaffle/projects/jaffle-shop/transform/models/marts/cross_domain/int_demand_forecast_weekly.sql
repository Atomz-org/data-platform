with weekly_sales as (
    select
        product_id,
        {{ dbt.date_trunc("week", "sale_date") }} as sale_week,
        sum(units_sold) as weekly_quantity_sold,
        sum(daily_revenue) as weekly_revenue
    from {{ ref('fct_product_sales') }}
    group by product_id, {{ dbt.date_trunc("week", "sale_date") }}
),

with_moving_avg as (
    select
        product_id,
        sale_week,
        weekly_quantity_sold,
        weekly_revenue,
        avg(weekly_quantity_sold) over (
            partition by product_id
            order by sale_week
            rows between 4 preceding and 1 preceding
        ) as forecast_qty_4wk_avg,
        avg(weekly_revenue) over (
            partition by product_id
            order by sale_week
            rows between 4 preceding and 1 preceding
        ) as forecast_revenue_4wk_avg,
        stddev(weekly_quantity_sold) over (
            partition by product_id
            order by sale_week
            rows between 4 preceding and 1 preceding
        ) as qty_stddev_4wk,
        row_number() over (
            partition by product_id
            order by sale_week desc
        ) as recency_rank
    from weekly_sales
)

select
    product_id,
    sale_week,
    weekly_quantity_sold as actual_quantity,
    weekly_revenue as actual_revenue,
    round(coalesce(forecast_qty_4wk_avg, 0)::numeric, 2) as forecasted_quantity,
    round(coalesce(forecast_revenue_4wk_avg, 0)::numeric, 2) as forecasted_revenue,
    round(coalesce(qty_stddev_4wk, 0)::numeric, 2) as quantity_volatility,
    case
        when coalesce(forecast_qty_4wk_avg, 0) > 0
            then round(
                ((weekly_quantity_sold - forecast_qty_4wk_avg)
                / forecast_qty_4wk_avg * 100), 2
            )
        else 0
    end as forecast_error_pct,
    recency_rank
from with_moving_avg
