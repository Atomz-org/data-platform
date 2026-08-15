with

daily_sales as (

    select * from {{ ref('int_product_sales_daily') }}

),

monthly_sales as (

    select
        product_id,
        {{ dbt.date_trunc('month', 'sale_date') }} as sales_month,
        extract(month from sale_date) as month_number,
        sum(units_sold) as monthly_quantity,
        sum(daily_revenue) as monthly_revenue
    from daily_sales
    group by 1, 2, 3

),

annual_avg as (

    select
        product_id,
        avg(monthly_quantity) as avg_monthly_quantity,
        avg(monthly_revenue) as avg_monthly_revenue
    from monthly_sales
    group by 1

),

final as (

    select
        ms.product_id,
        ms.sales_month,
        ms.month_number,
        ms.monthly_quantity,
        ms.monthly_revenue,
        aa.avg_monthly_quantity,
        case
            when aa.avg_monthly_quantity > 0
                then round(cast(ms.monthly_quantity / aa.avg_monthly_quantity as {{ dbt.type_float() }}), 2)
            else null
        end as seasonality_index,
        case
            when aa.avg_monthly_quantity > 0 and ms.monthly_quantity / aa.avg_monthly_quantity > 1.3
                then 'peak_season'
            when aa.avg_monthly_quantity > 0 and ms.monthly_quantity / aa.avg_monthly_quantity < 0.7
                then 'off_season'
            else 'normal_season'
        end as season_type
    from monthly_sales as ms
    left join annual_avg as aa
        on ms.product_id = aa.product_id

)

select * from final
