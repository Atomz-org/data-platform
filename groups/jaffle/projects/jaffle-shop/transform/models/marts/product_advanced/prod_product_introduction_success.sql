with

ps as (
    select * from {{ ref('fct_product_sales') }}
),

product_launch as (

    select
        product_id,
        min(sale_date) as launch_date
    from {{ ref('fct_product_sales') }}
    group by 1

),

first_90_days as (

    select
        pl.product_id,
        pl.launch_date,
        sum(ps.units_sold) as first_90_day_qty,
        sum(ps.daily_revenue) as first_90_day_revenue,
        count(distinct ps.sale_date) as active_sale_days
    from product_launch as pl
    inner join ps
        on pl.product_id = ps.product_id
        and ps.sale_date between pl.launch_date and {{ dbt.dateadd('day', '90', 'pl.launch_date') }}
    group by 1, 2

),

products as (

    select product_id, product_name, product_type
    from {{ ref('stg_products') }}

),

thresholds as (

    select avg(first_90_day_qty) as avg_90_day_qty from first_90_days

),

final as (

    select
        f.product_id,
        p.product_name,
        p.product_type,
        f.launch_date,
        f.first_90_day_qty,
        f.first_90_day_revenue,
        f.active_sale_days,
        t.avg_90_day_qty,
        case
            when f.first_90_day_qty >= t.avg_90_day_qty * 1.5 then 'strong_launch'
            when f.first_90_day_qty >= t.avg_90_day_qty then 'successful_launch'
            when f.first_90_day_qty >= t.avg_90_day_qty * 0.5 then 'weak_launch'
            else 'failed_launch'
        end as launch_status
    from first_90_days as f
    inner join products as p on f.product_id = p.product_id
    cross join thresholds as t

)

select * from final
