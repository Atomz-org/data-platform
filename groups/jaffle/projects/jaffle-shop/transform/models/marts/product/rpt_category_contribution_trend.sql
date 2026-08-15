with

product_sales_daily as (

    select * from {{ ref('int_product_sales_daily') }}

),

menu_items as (

    select * from {{ ref('stg_menu_items') }}

),

menu_categories as (

    select * from {{ ref('stg_menu_categories') }}

),

sales_with_category as (

    select
        {{ dbt.date_trunc('month', 'psd.sale_date') }} as sale_month,
        mc.menu_category_id,
        mc.category_name,
        sum(psd.units_sold) as monthly_units_sold,
        sum(psd.daily_revenue) as monthly_revenue

    from product_sales_daily as psd
    inner join menu_items as mi
        on psd.product_id = mi.product_id
    inner join menu_categories as mc
        on mi.menu_category_id = mc.menu_category_id
    group by
        {{ dbt.date_trunc('month', 'psd.sale_date') }},
        mc.menu_category_id,
        mc.category_name

),

with_shares as (

    select
        sale_month,
        menu_category_id,
        category_name,
        monthly_units_sold,
        monthly_revenue,
        sum(monthly_revenue) over (partition by sale_month) as total_monthly_revenue,
        monthly_revenue * 1.0
            / nullif(sum(monthly_revenue) over (partition by sale_month), 0)
            * 100 as revenue_share_pct

    from sales_with_category

),

with_totals as (

    select
        sale_month,
        menu_category_id,
        category_name,
        monthly_units_sold,
        monthly_revenue,
        total_monthly_revenue,
        revenue_share_pct,
        lag(monthly_revenue) over (
            partition by menu_category_id order by sale_month
        ) as prev_month_revenue,
        case
            when lag(monthly_revenue) over (
                partition by menu_category_id order by sale_month
            ) > 0
            then (monthly_revenue - lag(monthly_revenue) over (
                partition by menu_category_id order by sale_month
            )) / lag(monthly_revenue) over (
                partition by menu_category_id order by sale_month
            ) * 100
            else null
        end as revenue_mom_change_pct,
        lag(revenue_share_pct) over (
            partition by menu_category_id order by sale_month
        ) as prev_month_share_pct

    from with_shares

),

final as (

    select
        sale_month,
        menu_category_id,
        category_name,
        monthly_units_sold,
        monthly_revenue,
        total_monthly_revenue,
        revenue_share_pct,
        prev_month_revenue,
        revenue_mom_change_pct,
        prev_month_share_pct,
        revenue_share_pct - coalesce(prev_month_share_pct, revenue_share_pct) as share_change_ppt,
        case
            when revenue_share_pct > coalesce(prev_month_share_pct, revenue_share_pct) + 2
            then 'gaining_share'
            when revenue_share_pct < coalesce(prev_month_share_pct, revenue_share_pct) - 2
            then 'losing_share'
            else 'stable_share'
        end as share_trend

    from with_totals

)

select * from final
