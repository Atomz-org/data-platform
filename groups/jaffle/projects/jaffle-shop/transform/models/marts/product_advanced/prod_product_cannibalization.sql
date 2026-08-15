with

pt as (
    select * from {{ ref('stg_products') }}
),

daily_sales as (

    select
        product_id,
        sale_date,
        units_sold,
        daily_revenue
    from {{ ref('fct_product_sales') }}

),

products as (

    select
        product_id,
        product_name,
        product_type
    from {{ ref('stg_products') }}

),

product_launch as (

    select
        product_id,
        min(sale_date) as launch_date
    from daily_sales
    group by 1

),

-- For each product type, check if new products reduced existing product sales
pre_post_comparison as (

    select
        ds.product_id,
        p.product_name,
        p.product_type,
        pl.launch_date,
        sum(case when ds.sale_date < pl.launch_date then ds.units_sold else 0 end) as pre_launch_qty,
        sum(case when ds.sale_date >= pl.launch_date then ds.units_sold else 0 end) as post_launch_qty,
        count(distinct case when ds.sale_date < pl.launch_date then ds.sale_date end) as pre_launch_days,
        count(distinct case when ds.sale_date >= pl.launch_date then ds.sale_date end) as post_launch_days
    from daily_sales as ds
    inner join products as p on ds.product_id = p.product_id
    inner join product_launch as pl on pl.product_id != ds.product_id
    inner join products as pl_prod on pl.product_id = pl_prod.product_id
    where p.product_type = pl_prod.product_type
    group by 1, 2, 3, 4

),

final as (

    select
        product_id,
        product_name,
        product_type,
        launch_date as new_product_launch_date,
        pre_launch_qty,
        post_launch_qty,
        case when pre_launch_days > 0 then cast(pre_launch_qty as {{ dbt.type_float() }}) / pre_launch_days else 0 end as avg_daily_pre,
        case when post_launch_days > 0 then cast(post_launch_qty as {{ dbt.type_float() }}) / post_launch_days else 0 end as avg_daily_post,
        case
            when pre_launch_days > 0 and post_launch_days > 0
                and cast(pre_launch_qty as {{ dbt.type_float() }}) / pre_launch_days > 0
            then ((cast(post_launch_qty as {{ dbt.type_float() }}) / post_launch_days)
                - (cast(pre_launch_qty as {{ dbt.type_float() }}) / pre_launch_days))
                / (cast(pre_launch_qty as {{ dbt.type_float() }}) / pre_launch_days) * 100
            else null
        end as sales_change_pct
    from pre_post_comparison
    where pre_launch_days > 0 and post_launch_days > 0

)

select * from final
