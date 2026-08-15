with

product_sales_daily as (

    select * from {{ ref('int_product_sales_daily') }}

),

final as (

    select
        sale_date,
        product_id,
        product_name,
        product_type,
        current_unit_price,
        units_sold,
        order_count,
        daily_revenue,
        sum(daily_revenue) over (
            partition by product_id
            order by sale_date
            rows between unbounded preceding and current row
        ) as cumulative_revenue,
        avg(units_sold) over (
            partition by product_id
            order by sale_date
            rows between 6 preceding and current row
        ) as rolling_7d_avg_units

    from product_sales_daily

)

select * from final
