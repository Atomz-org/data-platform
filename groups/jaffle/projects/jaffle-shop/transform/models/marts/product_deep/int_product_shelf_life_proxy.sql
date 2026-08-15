with

order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders as (

    select
        order_id,
        ordered_at
    from {{ ref('stg_orders') }}

),

products as (

    select
        product_id,
        product_name,
        product_type
    from {{ ref('stg_products') }}

),

daily_sales as (

    select
        oi.product_id,
        o.ordered_at as sale_date,
        count(oi.order_item_id) as units_sold
    from order_items as oi
    inner join orders as o
        on oi.order_id = o.order_id
    group by 1, 2

),

sale_gaps as (

    select
        product_id,
        sale_date,
        lag(sale_date) over (partition by product_id order by sale_date) as prev_sale_date,
        case
            when lag(sale_date) over (partition by product_id order by sale_date) is not null
                then {{ dbt.datediff(
                    "lag(sale_date) over (partition by product_id order by sale_date)",
                    "sale_date",
                    "day"
                ) }}
            else null
        end as days_between_sales
    from daily_sales

),

final as (

    select
        sg.product_id,
        p.product_name,
        p.product_type,
        avg(sg.days_between_sales) as avg_days_between_sales,
        max(sg.days_between_sales) as max_gap_days,
        case
            when avg(sg.days_between_sales) <= 1 then 'daily_demand'
            when avg(sg.days_between_sales) <= 3 then 'high_turnover'
            when avg(sg.days_between_sales) <= 7 then 'weekly_demand'
            else 'low_turnover'
        end as freshness_tier
    from sale_gaps as sg
    inner join products as p
        on sg.product_id = p.product_id
    where sg.days_between_sales is not null
    group by 1, 2, 3

)

select * from final
