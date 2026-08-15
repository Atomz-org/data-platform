with

ps as (
    select * from {{ ref('fct_product_sales') }}
),

sales as (

    select
        ps.product_id,
        ps.sale_date,
        ps.units_sold,
        ps.daily_revenue,
        {{ dbt.date_trunc('month', 'ps.sale_date') }} as sale_month
    from ps

),

products as (

    select product_id, product_name, product_type
    from {{ ref('stg_products') }}

),

monthly as (

    select
        s.sale_month,
        p.product_type,
        sum(s.units_sold) as monthly_qty,
        sum(s.daily_revenue) as monthly_revenue
    from sales as s
    inner join products as p on s.product_id = p.product_id
    group by 1, 2

),

monthly_total as (

    select sale_month, sum(monthly_revenue) as total_revenue
    from monthly
    group by 1

),

final as (

    select
        m.sale_month,
        m.product_type,
        m.monthly_qty,
        m.monthly_revenue,
        mt.total_revenue,
        case
            when mt.total_revenue > 0
            then m.monthly_revenue / mt.total_revenue * 100
            else 0
        end as revenue_share_pct,
        lag(m.monthly_revenue) over (partition by m.product_type order by m.sale_month) as prev_month_revenue,
        case
            when lag(m.monthly_revenue) over (partition by m.product_type order by m.sale_month) > 0
            then (m.monthly_revenue - lag(m.monthly_revenue) over (partition by m.product_type order by m.sale_month))
                / lag(m.monthly_revenue) over (partition by m.product_type order by m.sale_month) * 100
            else null
        end as mom_growth_pct
    from monthly as m
    inner join monthly_total as mt on m.sale_month = mt.sale_month

)

select * from final
