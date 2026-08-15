with

product_sales as (

    select * from {{ ref('int_product_sales_by_location') }}

),

monthly_sales as (

    select
        location_id,
        product_id,
        {{ dbt.date_trunc('month', 'sale_date') }} as sales_month,
        sum(units_sold) as total_quantity,
        sum(daily_revenue) as total_sales

    from product_sales
    group by location_id, product_id, {{ dbt.date_trunc('month', 'sale_date') }}

)

select
    location_id as store_id,
    product_id,
    sales_month,
    total_quantity,
    total_sales,
    rank() over (
        partition by location_id, sales_month
        order by total_sales desc
    ) as product_rank_in_store

from monthly_sales
